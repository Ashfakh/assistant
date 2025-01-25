from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from app.actor.actor import Actor
from app.dto.scheduler import SchedulerMemory
from app.dto.session import QueryDTO
from app.models.models import Scheduler
from app.services.chat_service import ChatService
from app.services.llm_factory import LLMFactory, LLMProvider
from langchain.schema import HumanMessage, SystemMessage
import structlog
from asgiref.sync import sync_to_async

logger = structlog.get_logger(__name__)

scheduler_prompt = """
You are a scheduler for an assistant. You need to create a scheduled reminder for the user. 
You need to identify the schedule time, schedule type and the schedule message who the reminder is for. The schedule can be for the user itself or his Son or Dad.
If you are not able to identify any of the required fields, Your user type is {user_type}.
you need to ask the user to provide the missing information one by one, Keep asking for the required information until you get all the information.
you can ask the user by setting message to the user. If all the information is available, set message to None.
Schedule type can be one of the following:
Recurring - The reminder is a recurring reminder.
One Time - The reminder is a one time reminder.
Other information:
timestamp : {timestamp}
"""

class SchedulerState(BaseModel):
    user_type: Optional[str] = None
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
        messages.append(SystemMessage(content=scheduler_prompt.format(user_type=query_dto.session_dto.active_user, timestamp=datetime.now().isoformat())))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        scheduler_state = await self.llm.ainvoke(messages)
        if scheduler_state.message:
            return scheduler_state.message
        else:
            await self.handle_scheduler(scheduler_state, query_dto)
            return "Thanks for using Vaani. Have a great day!, Your Scheduled reminder is set"
        
    async def handle_scheduler(self, scheduler_state: SchedulerState, query_dto: QueryDTO):
        logger.info("Scheduler State", scheduler_state=scheduler_state)
        
        # Convert datetime to cron expression
        hour = scheduler_state.schedule_time.hour
        minute = scheduler_state.schedule_time.minute
        day = scheduler_state.schedule_time.day
        month = scheduler_state.schedule_time.month
        day_of_week = scheduler_state.schedule_time.weekday()
        
        cron_expression = f"{minute} {hour} {day} {month} {day_of_week}"
        
        # Create and save the scheduler
        scheduler = await sync_to_async(Scheduler.objects.create)(
            recipient=query_dto.session_dto.active_user,
            schedule_time=scheduler_state.schedule_time,
            schedule_type=scheduler_state.schedule_type,
            schedule_message=scheduler_state.schedule_message,
            cron_expression=cron_expression
        )
        
        logger.info("Scheduler created", 
                    scheduler_id=scheduler.id,
                    schedule_time=scheduler.schedule_time,
                    cron_expression=scheduler.cron_expression)
    



