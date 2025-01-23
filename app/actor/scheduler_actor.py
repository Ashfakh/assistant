from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from app.actor.actor import Actor
from app.dto.scheduler import SchedulerMemory
from app.dto.session import QueryDTO
from app.services.chat_service import ChatService
from app.services.llm_factory import LLMFactory, LLMProvider
from langchain.schema import HumanMessage, SystemMessage
import structlog

logger = structlog.get_logger(__name__)

scheduler_prompt = """
You are a scheduler for a voice assistant. You need to create a scheduled reminder for the user. 
You need to identify the schedule time, schedule type and the schedule message. If you are not able to identify any of the required fields,
you need to ask the user to provide the missing information one by one, Keep asking for the required information until you get all the information.
you can ask the user by setting message to the user. If all the information is available, set message to None.
"""

class SchedulerState(BaseModel):
    schedule_time: Optional[datetime] = None
    schedule_type: Optional[str] = None
    schedule_message: Optional[str] = None
    message: Optional[str] = None


class SchedulerActor(Actor):
    def __init__(self, initial_memory: Optional[SchedulerMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        self.chat_service = ChatService()
        self.llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        ).with_structured_output(SchedulerState)

    async def _on_receive(self, query_dto: QueryDTO):
        messages = []
        messages.append(SystemMessage(content=scheduler_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        scheduler_state = await self.llm.ainvoke(messages)
        if scheduler_state.message:
            return scheduler_state.message
        else:
            self.handle_scheduler(scheduler_state, query_dto)
            return "Thanks for using Chottu. Have a great day!, Your Scheduled reminder is set"
        
    def handle_scheduler(self, scheduler_state: SchedulerState, query_dto: QueryDTO):
        logger.info("Scheduler State", scheduler_state=scheduler_state)
    



