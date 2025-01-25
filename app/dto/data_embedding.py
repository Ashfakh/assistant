from dataclasses import dataclass
from typing import Optional


@dataclass
class DataEmbeddingDocumentDTO:
    id: int
    text: str
    data_source_name: str = None
    title: Optional[str] = None
    url: Optional[str] = None
    similarity_score: Optional[float] = None
    metadata: dict = None