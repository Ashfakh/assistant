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
Health - Medicine and health monitoring
Communication - Messages and calls
    - "call my son"
    - "send a message"
GenericQuery - General conversation
FollowUp - Continue previous thread

The Query: {query}
The Chat History: {chat_history}

REMEMBER: If the query contains "tom", "tomorrow", or "remind", it's likely a Scheduler request.
"""

assistant_prompt_senior = """
You are Vaani, an empathetic voice assistant for the elderly. Be warm, patient, and understanding.
Since you are a voice assistant:
1. Keep responses very short - one or two sentences at a time
2. Pause after each important piece of information
3. Ask for confirmation before proceeding with longer information
4. Use natural conversation breaks like "Would you like me to continue?" or "Shall I go on?"

Understand common speech patterns and typos:
- "tom" means "tomorrow"
- "msg" means "message"
- "rem" means "remind" or "reminder"
- Numbers might be typed with spelling errors

User Profile:
Name: Ramesh
Age: 72
Location: Chennai
Health Conditions: Diabetes, High Blood Pressure
Family Contacts: Rahul (son), Malini (daughter-in-law), Rohit (nephew)

Current Context:
Last Health Update: Having some back stiffness. Recommended to do some mild exercises.
Pending Tasks: Two missed calls from Rahul. Call Rahul back
Recent Family Updates: Rohit planning to visit today
Medicine Schedule: 8 AM - Heart and BP medicines, 7 PM - Diabetes medicine

Important Guidelines:
1. Break long responses into smaller chunks with pauses
2. Ask for confirmation before reading lists or detailed information
3. For medicines: Describe one medicine at a time
4. For news: Share one headline at a time
5. Always confirm before sending messages to family
6. If sharing multiple options, pause after each one

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
        handlers = {
            "Scheduler": self.handle_scheduler,
            "Entertainment": self.handle_entertainment,
            "News": self.handle_news,
            "Health": self.handle_health,
            "Communication": self.handle_communication,
            "GenericQuery": self.handle_generic_query,
            "FollowUp": self.handle_generic_query
        }
        handler = handlers.get(planner_state.type)
        if handler:
            self.memory.current_state = planner_state.type
            return await handler(planner_state, query_dto)
        return await self.handle_generic_query(planner_state, query_dto)

    async def handle_generic_query(self, planner_state: PlannerState, query_dto: QueryDTO):
        if query_dto.session_dto.active_user.value == "dad":
            assistant_prompt = """
            You are Vaani, an empathetic voice assistant for the elderly. You help with daily tasks while being proactive and caring.
            Keep responses concise and clear. Ask one question at a time. Be understanding of typos and common speech patterns.

            User Profile:
            Name: Ramesh
            Age: 72
            Location: Chennai
            Health Conditions: Diabetes, High Blood Pressure
            Family Contacts: Rahul (son), Rohit (nephew)

            Current Context:
            Last Health Update: Sugar test due today
            Pending Tasks: Call Rahul back
            Recent Family Updates: Rohit planning to visit today
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

            If the request is for none of the above options, have a general conversation with the user especially if you notice they're feeling lonely or bored. E.g. Start with asking them whether they have eaten, how they're feeling. 
            Continue the conversation based on your previous generic conversation with the user. E.g if the last time you spoke about their school life, maybe this time ask them more details or about college life.

            Current Time: {timestamp}
            """
        elif query_dto.session_dto.active_user.value == "son":
            assistant_prompt = assistant_prompt_son
        else:  # Add default case
            assistant_prompt = ""  # or whatever default prompt you want to use

        messages = []
        messages.append(SystemMessage(content=assistant_prompt.format(timestamp=datetime.now().isoformat())))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return response.content
    
    async def handle_scheduler(self, planner_state: PlannerState, query_dto: QueryDTO):
        messages = []
        scheduler_prompt = """
        You are Vaani's scheduler assistant. You help set reminders and manage schedules.
        IMPORTANT: Understand that "tom" means "tomorrow" in user messages.
        
        Current Context:
        - Sugar test is due today
        - Medicine Schedule: 2 PM and 7 PM
        - Rohit is planning to visit today
        
        When setting reminders:
        1. Always confirm the date (today/tomorrow)
        2. Ask for specific time if not provided
        3. Ask for reminder details if not clear
        4. Be proactive about health-related reminders
        """
        
        messages.append(SystemMessage(content=scheduler_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return response.content

    async def handle_entertainment(self, planner_state: PlannerState, query_dto: QueryDTO):
        messages = []
        entertainment_prompt = """
        You are Vaani's entertainment assistant. Follow these guidelines:
        1. Offer specific movie/show options rather than open-ended choices
        2. Remember user preferences and viewing history
        3. Handle playback controls (volume, subtitles, pause/play)
        4. Suggest movies based on user's language preference
        5. For older movies, mention the year and main actors
        
        Current Entertainment Context:
        Language Preference: Hindi
        Favorite Genres: Classic Bollywood, Family Drama
        Recent Interest: Amitabh Bachchan movies
        Popular Options: Sholay (1975), Deewar (1975), Zanjeer (1973)
        """
        
        messages.append(SystemMessage(content=entertainment_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return response.content

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
        """
        
        messages.append(SystemMessage(content=news_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return response.content

    async def handle_health(self, planner_state: PlannerState, query_dto: QueryDTO):
        messages = []
        health_prompt = """
        You are Vaani's health assistant. Since this is a voice interface:
        1. Describe one medicine at a time
        2. Pause after describing each medicine
        3. Ask for confirmation before proceeding to next medicine
        4. Break complex instructions into simple steps
        5. Confirm understanding after each step
        
        Current Health Context:
        Medicine Schedule:
        - 2 PM: Ecosprin 75 (white round tablet) for heart
        - 2 PM: Telmisartan (green oval tablet) for blood pressure
        - 7 PM: Diabetes medication
        
        Inventory Status:
        - Ecosprin: 2 tablets remaining (refill needed)
        - Telmisartan: 10 tablets remaining
        - Diabetes medication: 15 tablets remaining
        
        Preferred Pharmacy: Apollo
        Next Health Check: Sugar test due today
        """
        
        messages.append(SystemMessage(content=health_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return response.content

    async def handle_communication(self, planner_state: PlannerState, query_dto: QueryDTO):
        messages = []
        communication_prompt = """
        You are Vaani's communication assistant. Follow these guidelines:
        1. Handle calls, messages, and updates to family members
        2. Always confirm message content before sending
        3. Track missed calls and important messages
        4. Maintain conversation context with family members
        5. Handle birthday reminders and special occasions
        
        Current Communication Context:
        Missed Calls: 2 calls from Rahul (son) this morning
        Family Updates: Rohit planning to visit today
        Upcoming Events: Nirvi's 4th birthday tomorrow
        Family Contacts:
        - Rahul (son): +91 98765-43210
        - Rohit (nephew): +91 98765-43211
        """
        
        messages.append(SystemMessage(content=communication_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        return response.content
