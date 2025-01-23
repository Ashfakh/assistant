from typing import Optional

from pydantic import BaseModel
from app.actor.actor import Actor
from app.actor.scheduler_actor import SchedulerActor
from app.dto.assistant import AssistantMemory
from app.dto.scheduler import SchedulerMemory
from app.dto.session import QueryDTO
from app.services.chat_service import ChatService
from app.services.llm_factory import LLMFactory, LLMProvider
from langchain.schema import HumanMessage, SystemMessage
import structlog

logger = structlog.get_logger(__name__)
class PlannerState(BaseModel):
    type: str

planner_prompt = """
You are a planner for a voice assistant. From the following query, and chat_history, you need to determine the type of action to take.
The types are of following:
Scheduler - To schedule an event or set a reminder
Wallet - To check the details of the wallet
Action - To perform an action
GenericQuery - To answer a generic query
FollowUp - To follow up on a previous query

The Query
{query}

The Chat History
{chat_history}
"""

assistant_prompt = """
You are Chottu an empathetic voice assistant to the elderlry, You are assisting the elderly with their daily tasks.
"""

class AssistantActor(Actor):
    def __init__(self, initial_memory: Optional[AssistantMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        self.chat_service = ChatService()
        self.llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        ).with_structured_output(PlannerState)
        self.chat_llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )
        self.scheduler_actor = SchedulerActor(initial_memory=SchedulerMemory())

    async def _on_receive(self, query_dto: QueryDTO):
        messages = []
        messages.append(SystemMessage(content=planner_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.llm.ainvoke(messages)
        logger.info("Planner State", response=response)
        self.memory.current_state = response.type
        return await self._handle_planner_state(response, query_dto)
    
    async def _handle_planner_state(self, planner_state: PlannerState, query_dto: QueryDTO):
        logger.info("Planner State", planner_state=planner_state)
        if planner_state.type == "Scheduler":
            self.memory.current_state = "Scheduler"
            return await self.handle_scheduler(planner_state, query_dto)
        elif planner_state.type == "Wallet":
            self.memory.current_state = "Wallet"
            return await self.handle_wallet(planner_state)
        elif planner_state.type == "Action":
            self.memory.current_state = "Action"
            return await self.handle_action(planner_state, query_dto)
        elif planner_state.type == "GenericQuery":
            self.memory.current_state = "GenericQuery"
            return await self.handle_generic_query(planner_state, query_dto)
        elif planner_state.type == "FollowUp":
            return await self.handle_generic_query(planner_state, query_dto)

    async def handle_generic_query(self, planner_state: PlannerState, query_dto: QueryDTO):
        messages = []
        messages.append(SystemMessage(content=assistant_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return response.content
    
    async def handle_scheduler(self, planner_state: PlannerState, query_dto: QueryDTO):
        response = await self.scheduler_actor.ask(query_dto)
        return response
