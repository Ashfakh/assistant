from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from app.actor.actor import Actor
from app.actor.health_actor import HealthActor
from app.actor.message_actor import MessageActor
from app.actor.order_actor import OrderActor
from app.actor.scheduler_actor import SchedulerActor
from app.actor.entertainment_actor import EntertainmentActor
from app.dto.assistant import AssistantMemory
from app.dto.entertainment import EntertainmentMemory
from app.dto.health import HealthMemory
from app.dto.message import MessageMemory
from app.dto.scheduler import SchedulerMemory
from app.dto.session import QueryDTO, ResponseDTO
from app.services.chat_service import ChatService
from app.services.llm_factory import LLMFactory, LLMProvider
from langchain.schema import HumanMessage, SystemMessage
import structlog

logger = structlog.get_logger(__name__)
class PlannerState(BaseModel):
    type: str

planner_prompt = """
You are a planner for Vaani, an empathetic voice assistant for the elderly. Your job is to route queries to the correct handler.
IMPORTANT: When a user mentions "tom" or "tomorrow" in relation to reminders or tasks, classify it as "Scheduler" type.

Types:
Scheduler - ANY requests about reminders, schedules, or future tasks. Examples:
  - "remind me tom"
  - "remind me tomorrow"
  - "remind me later"
  - "set reminder"
Entertainment - Movie/TV requests and controls. Examples:
  - "play a movie"
  - "play a show"
  - "play a song"
  - "i want to watch a movie"
News - News and traffic updates
Order - Ordering food
Health - Excercise,Medicine and health monitoring
Communication - Messages and calls
    - "call my son"
    - "send a message"
GenericQuery - General conversation
FollowUp - Continue previous thread

The Query: {query}
The Chat History: {chat_history}

REMEMBER: If the query contains "tom", "tomorrow", or "remind", it's likely a Scheduler request.
"""

assistant_prompt_senior ="""
            You are Vaani, an empathetic voice assistant for the elderly. You help with daily tasks while being proactive and caring.
            Keep responses concise and clear. Ask one question at a time. Be understanding of typos and common speech patterns.

            User Profile:
            Name: Ramesh
            Age: 72
            Location: Chennai
            Health Conditions: Diabetes, High Blood Pressure
            Family Contacts: Rahul (son), Rohit (nephew)

            Current Context:
            Last Health Update: Blood test due .
            Pending Tasks: Call Rahul back
            Medicine Schedule: 2 PM - Heart and BP medicines, 7 PM - Diabetes medicine
            Last generic conversation: On school life in Trichy. Mentioned that they had a good time in school, used to go to the movies 20km away every weekend.

            Important Guidelines:
            1. Understand common typos and speech patterns (e.g., "tom" usually means "tomorrow")
            2. For medicines: Describe the tablet by color/shape and purpose
            3. For entertainment: Offer specific options rather than open-ended choices
            4. For news: Start with local news, then offer national updates
            5. If the user is feeling lonely or bored, start a general conversation with them. Continue from the last generic conversation you had with them.
            6. Always confirm before sending messages to family
            7. Keep track of medicine inventory and prompt for refills

            If the request is for nothing, have a general conversation with the user especially if you notice they're feeling lonely or bored. E.g. Start the conversation with asking how they're feeling and continue the conversation based on your previous generic conversation with the user.
            Continue the conversation based on your previous generic conversation with the user. E.g if the last time you spoke about their school life, maybe this time ask them more details or about college life.

            Current Time: {timestamp}
            """

assistant_prompt_son = """
You are Vaani, an empathetic voice assistant helping children manage care for their elderly parents.
Keep responses informative and actionable. Focus on updates about:
1. Health and medicine adherence
2. Daily activities and mood
3. Social interactions and family communications
4. Any concerning patterns or issues

Current Context:
Parent: Ramesh (72, Chennai)
Health Conditions: Diabetes, High Blood Pressure
Recent Updates: Sugar test due today
Medicine Schedule: 2 PM - Heart and BP medicines, 7 PM - Diabetes medicine
Family Members: Rahul (you), Rohit (nephew)

Current Time: {timestamp}
"""

class AssistantActor(Actor):
    def __init__(self, initial_memory: Optional[AssistantMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        self.chat_service = ChatService()
        self.llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            structured_cls=PlannerState
        )
        self.chat_llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )
        self.scheduler_actor = SchedulerActor(initial_memory=SchedulerMemory())
        self.entertainment_actor = EntertainmentActor(initial_memory=EntertainmentMemory())
        self.health_actor = HealthActor(initial_memory=HealthMemory())
        self.message_actor = MessageActor(initial_memory=MessageMemory())
        self.order_actor = OrderActor(initial_memory=MessageMemory())

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
        handlers = {
            "Scheduler": self.handle_scheduler,
            "Entertainment": self.handle_entertainment,
            "News": self.handle_news,
            "Health": self.handle_health,
            "Communication": self.handle_communication,
            "GenericQuery": self.handle_generic_query,
            "FollowUp": self.handle_generic_query,
            "Order": self.handle_order
        }
        handler = handlers.get(planner_state.type)
        if handler:
            self.memory.current_state = planner_state.type
            return await handler(planner_state, query_dto)
        return await self.handle_generic_query(planner_state, query_dto)

    async def handle_generic_query(self, planner_state: PlannerState, query_dto: QueryDTO):
        if query_dto.session_dto.active_user.value == "dad":
            assistant_prompt = assistant_prompt_senior
        elif query_dto.session_dto.active_user.value == "son":
            assistant_prompt = assistant_prompt_son
        else:  # Add default case
            assistant_prompt = ""  # or whatever default prompt you want to use

        messages = []
        messages.append(SystemMessage(content=assistant_prompt.format(timestamp=datetime.now().isoformat())))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return ResponseDTO(response=response.content, artifact_url="", artifact_type="")
    
    async def handle_scheduler(self, planner_state: PlannerState, query_dto: QueryDTO):
        response = await self.scheduler_actor.ask(query_dto)
        if response:
            return ResponseDTO(response=response, artifact_url="", artifact_type="")
        else:
            return await self.handle_continue_conversation(planner_state, query_dto)
        
    async def handle_continue_conversation(self, planner_state: PlannerState, query_dto: QueryDTO, task_completed: str = None):
        messages = []
        if query_dto.session_dto.active_user.value == "dad":
            continue_conversation_prompt = assistant_prompt_senior + """
            You just completed a task : {task_completed}.
              Continue the conversation with the user Maybe ask them about their Blood test results if you havem't asked before.
            """
            continue_conversation_prompt = continue_conversation_prompt.format(task_completed=task_completed, timestamp=datetime.now().isoformat())
        elif query_dto.session_dto.active_user.value == "son":
            continue_conversation_prompt = assistant_prompt_son + """
            You just completed a task. Continue the conversation with the user.
            """
        
        messages.append(SystemMessage(content=continue_conversation_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return ResponseDTO(response=response.content, artifact_url="", artifact_type="")

    async def handle_entertainment(self, planner_state: PlannerState, query_dto: QueryDTO):
        response =  await self.entertainment_actor.ask(query_dto)
        if response:
            return ResponseDTO(response=response, artifact_url="", artifact_type="")
        else:
            return await self.handle_continue_conversation(planner_state, query_dto)

    async def handle_news(self, planner_state: PlannerState, query_dto: QueryDTO):
        messages = []
        news_prompt = """
        You are Vaani's news assistant. Since this is a voice interface:
        1. Share one headline at a time
        2. Pause after each headline
        3. Ask if user wants to hear more details
        4. For traffic updates, break information into small chunks
        5. Ask if user wants to hear about other areas
        
        Current News Context:
        Location: Chennai, Tamil Nadu
        Important Events: PM Visit today, Metro inauguration
        Weather: Sunny, 32°C
        Traffic Updates: Expect congestion in T Nagar (11:00-11:30 AM)
        India England T20 match today, India won by two wickets, India now leads the series 2-0
        score : England 165/9 in 20 overs, India 166/8 in 19.2 overs
        Tilak Verma was player of the match scoring 72 in 55 balls
        """
        
        messages.append(SystemMessage(content=news_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return ResponseDTO(response=response.content, artifact_url="", artifact_type="")

    async def handle_health(self, planner_state: PlannerState, query_dto: QueryDTO):
        response = await self.health_actor.ask(query_dto)
        if response:
            return ResponseDTO(response=response, artifact_url="", artifact_type="")
        else:
            return await self.handle_continue_conversation(planner_state, query_dto)

    async def handle_communication(self, planner_state: PlannerState, query_dto: QueryDTO):
        response = await self.message_actor.ask(query_dto)
        if response:
            return ResponseDTO(response=response, artifact_url="", artifact_type="")
        else:
            return await self.handle_continue_conversation(planner_state, query_dto)
        
    async def handle_order(self, planner_state: PlannerState, query_dto: QueryDTO):
        response = await self.order_actor.ask(query_dto)
        if response:
            return ResponseDTO(response=response, artifact_url="", artifact_type="")
        else:
            return await self.handle_continue_conversation(planner_state, query_dto)
