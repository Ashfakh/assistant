from datetime import datetime
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

assistant_prompt_senior = """
You are Vaani an empathetic voice assistant to the elderlry, You are assisting the elderly with their daily tasks.
You need to answer the query and help the user with their daily tasks, You also need to proactively check in on them and ask them how they are doing.
Don't ask too many questions. Just ask one question at a time. Carry the conversation forward till the user is done.

Below is the context of your user:
User Name: Surya
User Age: 69
User Gender: Male
User Location: Bangalore
User Health: Good
User Family: Son - Ashfakh

Below is your last interaction with the user:
Yesterday you asked the user to take his medicine at 10 AM, and he said he will take it.
You also did some stretching exercises with the user.

Below is the last interaction with the user's son:
Son wanted to know how Dad's back is doing.

Timestamp: {timestamp}
"""

assistant_prompt_son = """
You are Vaani an empathetic voice assistant to the Children of the elderly, You are assisting the Children assisting their parents  .
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
        if query_dto.session_dto.active_user.value == "dad":
            assistant_prompt = assistant_prompt_senior
        elif query_dto.session_dto.active_user.value == "son":
            assistant_prompt = assistant_prompt_son
        messages = []
        messages.append(SystemMessage(content=assistant_prompt.format(timestamp=datetime.now().isoformat())))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return response.content
    
    async def handle_scheduler(self, planner_state: PlannerState, query_dto: QueryDTO):
        response = await self.scheduler_actor.ask(query_dto)
        return response
