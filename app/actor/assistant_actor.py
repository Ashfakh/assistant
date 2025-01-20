from typing import Optional
from app.actor.actor import Actor
from app.dto.assistant import AssistantMemory
from app.dto.coordinator import CoordinatorMemory
from app.dto.session import QueryDTO
from app.services.chat_service import ChatService


class AssistantActor(Actor):
    def __init__(self, initial_memory: Optional[AssistantMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        self.chat_service = ChatService()

    def _on_receive(self, query_dto: QueryDTO):
        return self.chat_service.get_chat_response(query_dto.message, query_dto.session_dto.chat_history)



