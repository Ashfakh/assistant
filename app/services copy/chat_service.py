from app.django_orm import settings
from ..dto.chat import ChatMessage
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, BaseMessage, AIMessage

class ChatService:
    def __init__(self):
        self.chat = ChatOpenAI(
            model="gpt-4",
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.7
        )

    async def get_chat_response(self, message: str, chat_history: list[ChatMessage]) -> str:
        messages = [
            SystemMessage(content="You are a helpful voice assistant."),
        ]
        
        messages.extend(self.create_messages(chat_history))
        messages.append(HumanMessage(content=message))
        
        response = await self.chat.ainvoke(messages)
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
