from ..config import settings
from ..models.chat import ChatMessage
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

class ChatService:
    def __init__(self):
        self.chat = ChatOpenAI(
            model="gpt-4",
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.7
        )

    async def get_chat_response(self, message: str, session_id: str, db: Session) -> str:
        messages = [
            SystemMessage(content="You are a helpful voice assistant."),
            HumanMessage(content=message)
        ]
        
        response = await self.chat.ainvoke(messages)
        assistant_message = response.content
        
        chat_message = ChatMessage(
            session_id=session_id,
            user_message=message,
            assistant_message=assistant_message
        )
        db.add(chat_message)
        db.commit()
        
        return assistant_message 