from app.services.llm_factory import LLMFactory, LLMProvider
from ..dto.chat import ChatMessage
from langchain.schema import HumanMessage, SystemMessage, BaseMessage, AIMessage

class ChatService:
    def __init__(self):
        self.llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )

    async def get_chat_response(self, message: str, chat_history: list[ChatMessage]) -> str:
        messages = [
            SystemMessage(content="You are a helpful voice assistant."),
        ]
        
        messages.extend(self.create_messages(chat_history))
        messages.append(HumanMessage(content=message))
        
        response = await self.llm.ainvoke(messages)
        assistant_message = response.content
        
        return assistant_message 
    
    def create_messages(self, chat_history: list[ChatMessage]) -> list[BaseMessage]:
        messages = []
        for message in chat_history:
            if message.role == "user":
                messages.append(HumanMessage(content=message.content))
            else:
                messages.append(AIMessage(content=message.content))
        return messages
