from typing import List, Union

from django.db import models
from app.core import settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI



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
    ):
        if llm_provider == LLMProvider.OPENAI:
            return ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=model_name,
                temperature=temperature,
                max_retries=max_retries,
                max_tokens=max_tokens,
                streaming=streaming,
                timeout=timeout,
            )
        elif llm_provider == LLMProvider.ANTHROPIC:
            return ChatAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model=model_name,
                temperature=temperature,
                max_retries=max_retries,
                max_tokens=max_tokens,
                streaming=streaming,
                timeout=timeout,
            )

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
