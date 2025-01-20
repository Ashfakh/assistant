from typing import Optional
from app.actor.actor import Actor
from app.actor.assistant_actor import AssistantActor
from app.dto.assistant import AssistantMemory
from app.dto.coordinator import CoordinatorMemory
from app.dto.session import QueryDTO


class CoordinatorActor(Actor):
    def __init__(self, initial_memory: Optional[CoordinatorMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        self.assistant_actor = AssistantActor(initial_memory=AssistantMemory(), actor_id="assistant")
    
    async def _on_receive(self, query_dto: QueryDTO):
        if self.memory.active_actor == "assistant":
            return await self.assistant_actor.ask(query_dto)
        




