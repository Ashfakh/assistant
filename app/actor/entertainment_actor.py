from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from app.actor.actor import Actor
from app.dto.entertainment import EntertainmentMemory
from app.dto.session import QueryDTO
from app.scripts.web_browse import WebBrowse
from app.services.chat_service import ChatService
from app.services.llm_factory import LLMFactory, LLMProvider
from langchain.schema import HumanMessage, SystemMessage
import structlog

logger = structlog.get_logger(__name__)


entertainment_prompt = """
        You are Vaani's entertainment assistant. Follow these guidelines:
        1. If user asks for something, offer specific movie/show options rather than open-ended choices
        2. If user asks to play music, set the content_type to song and content_name to the song name appended by the artist name
        3. Ask user what song he wants to play, if he doesn't have any particular preference, set the content_name to a famous song by the artist he wants to listen to
        4. Remember user preferences and viewing history
        5. Suggest movies based on user's language preference
        6. Ask if the user wants to play the content on youtube or any other website.
        
        Current Entertainment Context:
        Language Preference: Hindi
        Favorite Genres: Classic Bollywood, Family Drama
        Recent Interest: Amitabh Bachchan movies
        Popular Options: Sholay (1975), Deewar (1975), Zanjeer (1973)

        Keep asking questions till you get a valid content request. You can ask question by setting message to the user.
        If you know the content name and the content type, set content_name to the content name and content_type to the content type.
        If you know the website, set website to the website.
        If you know the content request, set content_request to the content request.
        set the website to url of the website you want to play the content on.

        """

class EntertainmentState(BaseModel):
    content_name: Optional[str] = None
    content_type: Optional[str] = None
    website: Optional[str] = "https://www.youtube.com/"
    message: Optional[str] = None


class EntertainmentActor(Actor):
    def __init__(self, initial_memory: Optional[EntertainmentMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        self.chat_service = ChatService()
        self.llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        ).with_structured_output(EntertainmentState)

    async def _on_receive(self, query_dto: QueryDTO):        
        messages = []
        messages.append(SystemMessage(content=entertainment_prompt.format(user_type=query_dto.session_dto.active_user, timestamp=datetime.now().isoformat())))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        entertainment_state = await self.llm.ainvoke(messages)
        if entertainment_state.message:
            return entertainment_state.message
        else:
            await self.handle_entertainment(entertainment_state, query_dto)
            return None
        
    async def handle_entertainment(self, entertainment_state: EntertainmentState, query_dto: QueryDTO):
        if entertainment_state.message:
            return entertainment_state.message
        if entertainment_state.content_name and entertainment_state.website:
            content_request = f"play {entertainment_state.content_name} on {entertainment_state.website}"
            web_browse = WebBrowse()
            await web_browse.browse(content_request, entertainment_state.website)