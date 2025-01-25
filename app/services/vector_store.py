import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Optional,
    List,
    Any,
    Sequence,
    Iterable,
    Dict,
    Union,
    ClassVar,
    Collection,
)

from django.db import transaction
from django.db.models import Q
from langchain_core.documents import Document as LangChainDocument
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from pgvector.django import CosineDistance, L2Distance, MaxInnerProduct
from pydantic import model_validator
from asgiref.sync import sync_to_async

from app.dto.data_embedding import DataEmbeddingDocumentDTO
from app.models.models import DataEmbedding


class DistanceStrategy(Enum):
    """Enumerator of the Distance strategies."""

    EUCLIDEAN = "l2"
    COSINE = "cosine"
    MAX_INNER_PRODUCT = "inner"


DEFAULT_DISTANCE_STRATEGY = DistanceStrategy.COSINE


class PGVector:
    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY,
        logger: Optional[logging.Logger] = None,
    ):
        self.embedding_model = embedding_model
        self._distance_strategy = distance_strategy
        self.logger = logger or logging.getLogger(__name__)
        self.__post__init__()

    def __post__init__(self) -> None:
        self.embedding_function = OpenAIEmbeddings(model=self.embedding_model)
        self.embedding_field = (
            "embedding"  # Let factory handle it later based on embedding_model
        )

    @property
    def embeddings(self) -> Embeddings:
        return self.embedding_function

    def get_text_embeddings(self, texts: List[str]):
        return self.embeddings.embed_documents(
            texts
        )  # assuming Langchain Embedding Model

    def get_by_ids(self, ids: Sequence[int]) -> List[DataEmbedding]:
        return list(DataEmbedding.objects.filter(id__in=ids))

    @transaction.atomic
    def add_embeddings(
        self,
        texts: Iterable[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Add embeddings to the vector store.

        Args:
            texts: Iterable of strings to add to the vector store.
            embeddings: List of embeddings.
            metadatas: List of metadata associated with the texts.
            current_version: Current version of the data source.
            kwargs: Additional parameters for customization.

        Returns:
            List of IDs used for the documents.
        """

        if metadatas is None:
            metadatas = [{} for _ in texts]

        data_embeddings = []
        for text, metadata, embedding in zip(texts, metadatas, embeddings):
            title = metadata.get("title", "") or ""
            url = metadata.get("url", "") or ""
            text_override = metadata.get("text_override")

            if "text_override" in metadata:
                metadata.pop("text_override")


            # Remove any metadata that has null value
            metadata = {k: v for k, v in metadata.items() if v is not None}

            data_embeddings.append(
                DataEmbedding(
                    title=title,
                    url=url,
                    text=text,
                    text_override=text_override,
                    embedding=embedding,
                    metadata=metadata,
                )
            )
        # Use bulk_create to insert new records
        DataEmbedding.objects.bulk_create(data_embeddings)

        return [embedding.id for embedding in data_embeddings]

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        current_version: Optional[str] = None,
        **kwargs: Any,
    ) -> List[str]:
        """Run more texts through the embeddings and add to the vectorstore.

        Args:
            texts: Iterable of strings to add to the vectorstore.
            metadatas: Optional list of metadata associated with the texts.
            current_version: Current version of the data source.
            kwargs: vectorstore specific parameters

        Returns:
            List of ids from adding the texts into the vectorstore.
        """
        embeddings = self.embedding_function.embed_documents(list(texts))
        return self.add_embeddings(
            texts, embeddings, metadatas, current_version, **kwargs
        )

    @classmethod
    def from_documents(
        cls,
        documents: List[LangChainDocument],
        embedding_model: str,
        current_version: Optional[str] = None,
        *,
        distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY,
        **kwargs: Any,
    ):
        """Return PGVector Store initialized from documents and embeddings.
        Works with Langchain

        Args:
            documents: List of Documents to add to the vectorstore.
            embedding_model: EmbeddingModel function to use.
            distance_strategy: Distance strategy used
            kwargs: Additional keyword arguments.

        Returns:
            PGVector: PGVector store initialized from documents and embeddings.
        """
        texts = [d.page_content for d in documents]
        metadatas = [d.metadata for d in documents]
        return cls.from_texts(
            texts,
            embedding_model,
            metadatas,
            current_version,
            distance_strategy=distance_strategy,
            **kwargs,
        )

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding_model: str,
        metadatas: Optional[List[dict]] = None,
        current_version: Optional[str] = None,
        *,
        distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY,
        **kwargs: Any,
    ):
        """Return PGVector store initialized from documents and embeddings."""
        return cls.__from(
            texts,
            embedding_model,
            metadatas,
            current_version,
            distance_strategy,
            **kwargs,
        )

    @classmethod
    def __from(
        cls,
        texts: List[str],
        embedding_model: str,
        metadatas: Optional[List[dict]] = None,
        distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY,
        **kwargs: Any,
    ):
        if not metadatas:
            metadatas = [{} for _ in texts]

        store = cls(
            embedding_model=embedding_model,
            distance_strategy=distance_strategy,
            **kwargs,
        )

        embeddings = store.get_text_embeddings(texts)
        store.add_embeddings(
            texts, embeddings, metadatas, **kwargs
        )

        return store

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
        **kwargs: Any,
    ) -> List[DataEmbeddingDocumentDTO]:
        """Run similarity search with PGVector with distance.

        Args:
            query (str): Query text to search for.
            k (int): Number of results to return. Defaults to 4.
            filter (Optional[Dict[str, str]]): Filter by metadata. Defaults to None.

        Returns:
            List of Documents most similar to the query.
        """
        embedding = self.embedding_function.embed_query(text=query)
        return self.similarity_search_with_score_by_vector(
            embedding=embedding,
            k=k,
            filter=filter,
        )

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
        score_threshold: Optional[float] = None,
    ) -> List[DataEmbeddingDocumentDTO]:
        """Return docs most similar to query.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            filter (Optional[Dict[str, str]]): Filter by metadata. Defaults to None.
            score_threshold: Minimum score ofr document to be taken into account

        Returns:
            List of Documents most similar to the query and score for each.
        """
        embedding = self.embedding_function.embed_query(query)
        documents: List[DataEmbeddingDocumentDTO] = (
            self.similarity_search_with_score_by_vector(
                embedding=embedding, k=k, filter=filter
            )
        )

        if any(
            document.similarity_score < 0.0 or document.similarity_score > 1.0
            for document in documents
        ):
            self.logger.warning(
                "Relevance scores must be between" f" 0 and 1, got {documents}"
            )

        if score_threshold is not None:
            documents = [
                document
                for document in documents
                if document.similarity_score >= score_threshold
            ]
            if len(documents) == 0:
                self.logger.warning(
                    "No relevant docs were retrieved using the relevance score"
                    f" threshold {score_threshold}"
                )

        return documents

    def similarity_search_with_score_by_vector(
        self,
        embedding: List[float],
        k: int = 4,
        filter: Optional[dict] = None,
    ) -> List[DataEmbeddingDocumentDTO]:
        results = self.__query_collection(
            embedding=embedding, k=k, filter=filter
        )
        return self._results_to_docs(results)

    def __query_collection(
        self,
        embedding: List[float],
        k: int = 4,
        filter: Optional[Dict[str, str]] = None,
    ) -> List[DataEmbedding]:
        filters = Q()

        if filter:
            filter_clauses = self._create_filter_clause(filter)
            if filter_clauses is not None:
                filters &= filter_clauses

        results = (
            DataEmbedding.objects.filter(filters)
            .annotate(distance=self.distance_strategy(embedding))
            .order_by("distance")[:k]
        )
        return results

    def _results_to_docs(
        self, results: List[Union[DataEmbedding, any]]
    ) -> List[DataEmbeddingDocumentDTO]:
        """Return docs from results."""
        return [
            DataEmbeddingDocumentDTO(
                id=data_embedding.id,
                title=data_embedding.title,
                url=data_embedding.url,
                text=data_embedding.text_override or data_embedding.text,
                metadata=data_embedding.metadata,
                similarity_score=(
                    1 - data_embedding.distance
                    if self.embedding_function is not None
                    else None
                ),
            )
            for data_embedding in results
        ]

    def _create_filter_clause(self, filters: Any) -> Q:
        if isinstance(filters, dict):
            if len(filters) == 1:
                key, value = list(filters.items())[0]
                if key.startswith("$"):
                    if key.lower() == "$and":
                        and_clauses = [self._create_filter_clause(v) for v in value]
                        return Q(*and_clauses, connector=Q.AND)

                    elif key.lower() == "$or":
                        or_clauses = [self._create_filter_clause(v) for v in value]
                        return Q(*or_clauses, connector=Q.OR)

                    elif key.lower() == "$not":
                        if isinstance(value, dict):
                            return ~self._create_filter_clause(value)
                        elif isinstance(value, list):
                            not_clauses = [
                                ~self._create_filter_clause(item) for item in value
                            ]
                            return Q(*not_clauses, connector=Q.AND)

                    else:
                        raise ValueError(f"Invalid filter operator: {key}")

                else:
                    return self._handle_field_filter(key, value)

            else:
                and_clauses = [
                    self._handle_field_filter(k, v) for k, v in filters.items()
                ]
                return Q(*and_clauses, connector=Q.AND)

        else:
            raise ValueError(f"Expected a dictionary but got type: {type(filters)}")

    def distance_strategy(self, embedding) -> Any:
        if self._distance_strategy == DistanceStrategy.EUCLIDEAN:
            return L2Distance(self.embedding_field, embedding)
        elif self._distance_strategy == DistanceStrategy.COSINE:
            return CosineDistance(self.embedding_field, embedding)
        elif self._distance_strategy == DistanceStrategy.MAX_INNER_PRODUCT:
            return MaxInnerProduct(self.embedding_field, embedding)
        else:
            raise ValueError(
                f"Got unexpected value for distance: {self._distance_strategy}. "
                f"Should be one of {', '.join([ds.value for ds in DistanceStrategy])}."
            )

    @staticmethod
    def _handle_field_filter(field: str, value: Any) -> Q:
        if not isinstance(field, str):
            raise ValueError(
                f"Field should be a string but got: {type(field)} with value: {field}"
            )

        if field.startswith("$"):
            raise ValueError(
                f"Invalid filter condition. Expected a field but got an operator: {field}"
            )

        if not field.isidentifier():
            raise ValueError(
                f"Invalid field name: {field}. Expected a valid identifier."
            )

        prefix = f"metadata__{field}"

        if not isinstance(value, dict):
            return Q(**{f"{prefix}": value})

        if len(value) != 1:
            raise ValueError(
                "Invalid filter condition. Expected a dictionary with a single key."
            )

        operator, filter_value = list(value.items())[0]

        if operator == "$eq":
            return Q(**{f"{prefix}": filter_value})

        elif operator == "$ne":
            return ~Q(**{f"{prefix}": filter_value})

        elif operator == "$lt":
            return Q(**{f"{prefix}__lt": filter_value})

        elif operator == "$lte":
            return Q(**{f"{prefix}__lte": filter_value})

        elif operator == "$gt":
            return Q(**{f"{prefix}__gt": filter_value})

        elif operator == "$gte":
            return Q(**{f"{prefix}__gte": filter_value})

        elif operator == "$between":
            low, high = filter_value
            return Q(**{f"{prefix}__gte": low}) & Q(**{f"{prefix}__lte": high})

        elif operator in {"$in", "$nin"}:
            values = [str(val) for val in filter_value]
            if operator == "$in":
                return Q(**{f"{prefix}__in": values})
            else:
                return ~Q(**{f"{prefix}__in": values})

        elif operator in {"$like", "$ilike"}:
            if operator == "$like":
                return Q(**{f"{prefix}__icontains": filter_value})
            else:
                return Q(**{f"{prefix}__icontains": filter_value})

        elif operator == "$exists":
            if not isinstance(filter_value, bool):
                raise ValueError("Expected a boolean value for $exists.")
            if filter_value:
                return Q(**{f"{prefix}__isnull": False})
            else:
                return Q(**{f"{prefix}__isnull": True})

        elif operator == "$contains":
            if not isinstance(filter_value, list):
                raise ValueError("Expected a list value for $contains.")
            return Q(
                *[Q(**{f"{prefix}__contains": keyword}) for keyword in filter_value],
                _connector=Q.AND,
            )

        elif operator == "$icontains":
            if not isinstance(filter_value, list):
                raise ValueError("Expected a list value for $icontains.")
            return Q(
                *[Q(**{f"{prefix}__icontains": keyword}) for keyword in filter_value],
                _connector=Q.AND,
            )

        else:
            raise ValueError(f"Unsupported operator: {operator}")

    def as_retriever(self, **kwargs: Any):
        """
        Return PGVectorStoreRetriever initialized from this VectorStore.
        Note: mmr has not been implemented yet
        Args:
            **kwargs: Keyword arguments to pass to the search function.
                Can include:
                search_type (Optional[str]): Defines the type of search that
                    the Retriever should perform.
                    Can be "similarity" (default), or
                    "similarity_score_threshold".
                search_kwargs (Optional[Dict]): Keyword arguments to pass to the
                    search function. Can include things like:
                        k: Amount of documents to return (Default: 4)
                        score_threshold: Minimum relevance threshold
                            for similarity_score_threshold
                        fetch_k: Amount of documents to pass to MMR algorithm
                            (Default: 20)
                        lambda_mult: Diversity of results returned by MMR;
                            1 for minimum diversity and 0 for maximum. (Default: 0.5)
                        filter: Filter by document metadata

        Returns:
            PGVectorRetriever: Retriever class for VectorStore.

        Examples:

        code-block:: python
            # Only retrieve documents that have a relevance score
            # Above a certain threshold
            docsearch.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={'score_threshold': 0.8}
            )

            # Only get the single most similar document from the dataset
            docsearch.as_retriever(search_kwargs={'k': 1})

            # Use a filter to only retrieve documents from a specific paper
            docsearch.as_retriever(
                search_kwargs={'filter': {'paper_title':'GPT-4 Technical Report'}}
            )
        """
        return PGVectorRetriever(vectorstore=self, **kwargs)
    
@dataclass
class PGVectorRetriever:
    """Retriever class for PGVector Store."""

    vectorstore: PGVector
    """VectorStore to use for retrieval."""
    search_type: str = "similarity"
    """Type of search to perform. Defaults to "similarity"."""
    """List of DataSources to get the documents from"""
    search_kwargs: dict = field(default_factory=dict)
    """Keyword arguments to pass to the search function."""
    allowed_search_types: ClassVar[Collection[str]] = (
        "similarity",
        "similarity_score_threshold",
    )

    @model_validator(mode="before")
    def validate_search_type(cls, values: Dict) -> Dict:
        """Validate search type.

        Args:
            values: Values to validate.

        Returns:
            Values: Validated values.

        Raises:
            ValueError: If search_type is not one of the allowed search types.
            ValueError: If score_threshold is not specified with a float value(0~1)
        """
        search_type = values.get("search_type", "similarity")
        if search_type not in cls.allowed_search_types:
            raise ValueError(
                f"search_type of {search_type} not allowed. Valid values are: "
                f"{cls.allowed_search_types}"
            )
        if search_type == "similarity_score_threshold":
            score_threshold = values.get("search_kwargs", {}).get("score_threshold")
            if (score_threshold is None) or (not isinstance(score_threshold, float)):
                raise ValueError(
                    "`score_threshold` is not specified with a float value(0~1) "
                    "in `search_kwargs`."
                )
        return values


    def invoke(self, query, *args) -> List[DataEmbeddingDocumentDTO]:
        return self._get_relevant_documents(query, *args)

    async def arrf_invoke(
        self, queries: List[str], *args
    ) -> List[DataEmbeddingDocumentDTO]:
        tasks = [
            sync_to_async(self._get_relevant_documents)(query, *args)
            for query in queries
        ]
        doc_list = await asyncio.gather(*tasks)

        top_k = self.search_kwargs.get("k", None)

        return self.reciprocal_rank_fusion(doc_list)[:top_k]

    def rrf_invoke(self, queries: List[str], *args) -> List[DataEmbeddingDocumentDTO]:
        doc_list = []
        for query in queries:
            docs = self._get_relevant_documents(query, *args)
            doc_list.append(docs)

        top_k = self.search_kwargs.get("k", None)

        return self.reciprocal_rank_fusion(doc_list)[:top_k]

    def reciprocal_rank_fusion(
        self, results: List[List[DataEmbeddingDocumentDTO]], k: int = 60
    ) -> List[DataEmbeddingDocumentDTO]:
        """
        Reciprocal Rank Fusion that takes multiple lists of ranked `DataEmbeddingDocumentDTO` documents
        and an optional parameter k used in the RRF formula.
        Updates the `similarity_score` of each document with the new fused score.
        """
        # Dictionary to hold fused scores for each unique document by id
        fused_scores = defaultdict(float)
        doc_mapping = {}

        # Iterate through each list of ranked documents
        for docs in results:
            # Iterate through each document in the list, with its rank (position in the list)
            for rank, doc in enumerate(docs):
                # Use the document's ID as the key for fusion
                doc_id = doc.id
                # Keep track of the document instance (latest one encountered)
                doc_mapping[doc_id] = doc
                # Update the score of the document using the RRF formula: 1 / (rank + k)
                fused_scores[doc_id] += 1 / (rank + k)

        # Update the `similarity_score` of each document with the new fused score
        for doc_id, score in fused_scores.items():
            if doc_id in doc_mapping:
                doc_mapping[doc_id].similarity_score = (1 - score) * doc_mapping[
                    doc_id
                ].similarity_score

        # Sort the documents based on their fused scores in descending order
        reranked_results = [
            doc_mapping[doc_id]
            for doc_id in sorted(
                fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True
            )
        ]

        # Return the reranked results as a list of tuples, each containing the document and its fused score
        return reranked_results

    async def ainvoke(self, query, *args):
        """
        Usage Example
        ... :python codeblock
            doc_store = PGVector(EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL)
            retriever = doc_store.as_retriever(search_kwargs={"k": self.SIMILARITY_TOP_K})
            documents = await retriever.ainvoke(user_question)

        """
        return await sync_to_async(self._get_relevant_documents)(query, *args)

    def _get_relevant_documents(
        self, query: str, *args
    ) -> List[DataEmbeddingDocumentDTO]:
        if self.search_type == "similarity":
            return self.vectorstore.similarity_search(
                query, **self.search_kwargs
            )
        if self.search_type == "similarity_score_threshold":
            return self.vectorstore.similarity_search_with_relevance_scores(
                query, **self.search_kwargs
            )
        raise ValueError(f"search_type of {self.search_type} not allowed.")