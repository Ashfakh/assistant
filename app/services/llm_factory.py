import hashlib
from typing import List, Union

from django.db import models
from pydantic import BaseModel
from app.core import settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from django.core.cache import cache
import structlog    

logger = structlog.get_logger(__name__)


class LLMProvider(models.TextChoices):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMFactory:
    @staticmethod
    def get_chat_llm(
        llm_provider: LLMProvider,
        model_name: str,
        temperature=0.0,
        max_retries=3,
        max_tokens=500,
        streaming=True,
        timeout=None,
        structured_cls: BaseModel = None,
    ):
        if llm_provider == LLMProvider.OPENAI:
            return LLM(ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=model_name,
                temperature=temperature,
                max_retries=max_retries,
                max_tokens=max_tokens,
                streaming=streaming,
                timeout=timeout,
            ), structured_cls)
        elif llm_provider == LLMProvider.ANTHROPIC:
            return LLM(ChatAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model=model_name,
                temperature=temperature,
                max_retries=max_retries,
                max_tokens=max_tokens,
                streaming=streaming,
                timeout=timeout,
            ), structured_cls)

    @staticmethod
    def openai_to_anthropic_messages(
        messages: List[Union[SystemMessage, HumanMessage, AIMessage]]
    ):
        return [
            {
                "role": (
                    "user"
                    if isinstance(msg, HumanMessage)
                    else "assistant" if isinstance(msg, AIMessage) else "system"
                ),
                "content": msg.content,
            }
            for msg in messages
        ]
    
class LLM:
    def __init__(self, chat_model: BaseChatModel, structured_cls: BaseModel):
        self.llm = chat_model
        if structured_cls:
            self.llm = self.llm.with_structured_output(structured_cls)
        
    def invoke(self, messages: List[Union[SystemMessage, HumanMessage, AIMessage]]):
        return self.llm.invoke(messages)
        
    async def ainvoke(self, messages: List[Union[SystemMessage, HumanMessage, AIMessage]]):
        cached_response = self.get_cached_response(messages)
        if cached_response:
            return cached_response
        else:
            response = await self.llm.ainvoke(messages)
            self.set_cached_response(messages, response)
            return response
        
    def construct_message_hash(self, messages: List[Union[SystemMessage, HumanMessage, AIMessage]]):
        msg_str = "".join([msg.content for msg in messages])
        # logger.info("messages", messages=msg_str)
        return hashlib.sha256(msg_str.encode()).hexdigest()
        
    def get_cached_response(self, messages: List[Union[SystemMessage, HumanMessage, AIMessage]]):
        msg_hash = self.construct_message_hash(messages)
        logger.info("Getting cached response", message=msg_hash)
        return cache.get(msg_hash)
        
    def set_cached_response(self, messages: List[Union[SystemMessage, HumanMessage, AIMessage]], response: str):
        logger.info("Setting cached response", message=response)
        msg_hash = self.construct_message_hash(messages)
        cache.set(msg_hash, response, timeout=60*60*24)
