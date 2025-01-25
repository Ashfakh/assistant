from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from app.actor.actor import Actor
from app.dto.health import HealthMemory
from app.dto.session import QueryDTO
from app.scripts.web_browse import WebBrowse
from app.services.chat_service import ChatService
from app.services.llm_factory import LLMFactory, LLMProvider
from langchain.schema import HumanMessage, SystemMessage
import structlog

logger = structlog.get_logger(__name__)

health_prompt = """
        You are Vaani's health and exercise assistant. Since this is a voice interface:
        If the user asks for medicine, you need to set the activity to medicine.
        If you think the user is asking for exercise, you need to set the activity to exercise.
        If you need clarity on what the user is asking, you need to ask the user for it by setting the message to your question.
        Do not set the activity to medicine or exercise if you are not sure.
"""

medicine_prompt = """
        You are Vaani's health and exercise assistant. Since this is a voice interface:
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

exercise_script_prompt = """ You are Vaani's Exercise assistant.
 You are given a list of exercises and you need to select one of them based on the user's health context.
 You also need to construct an excercise script.
 Excercise script is a list of messages that you need to send to the user to be performed one by one

 {list_of_exercises}
"""

excercise_prompt = """ You are Vaani's Exercise assistant.
 You are walking the user through the excercise script. If the user acknowledges the excercise, you need to move to the next excercise by setting the message to the next excercise in the script. and set the user_acknowledged to True.
 If the user experiences difficulty, you need to ask the user to perform the excercise in a simpler way,
   encourage them like a coach. and set the user_acknowledged to False.
 You need to ask the user to perform the excercise. one by one. 
Once the user has performed all the excercises, you need to congratulate the user and set the user_acknowledged to True.
when you set the message, craft it in a way a calm helpful health coach would. Use ... for pauses. and use "" for Emphasizing parts if necessary
 {exercise_script}
"""

class HealthState(BaseModel):
    activity: Optional[str] = None
    message: Optional[str] = None

class ExerciseScript(BaseModel):
    messages: Optional[list[str]] = None

class ExerciseState(BaseModel):
    message: Optional[str] = None
    user_acknowledged: Optional[bool] = None




class HealthActor(Actor):
    def __init__(self, initial_memory: Optional[HealthMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        logger.info("Initializing HealthActor", actor_id=actor_id)
        self.chat_service = ChatService()
        self.health_llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        ).with_structured_output(HealthState)
        self.exercise_script_llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        ).with_structured_output(ExerciseScript)
        self.exercise_llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        ).with_structured_output(ExerciseState)
        self.chat_llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
        )

    async def _on_receive(self, query_dto: QueryDTO):   
        logger.info("Received query", message=query_dto.message)
        if not self.memory.current_activity:
            logger.debug("No current activity, determining activity type")
            messages = []
            messages.append(SystemMessage(content=health_prompt.format(user_type=query_dto.session_dto.active_user, timestamp=datetime.now().isoformat())))
            messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
            messages.append(HumanMessage(content=query_dto.message))
            health_state = await self.health_llm.ainvoke(messages)
            logger.info("Determined health state", activity=health_state.activity, message=health_state.message)
            if health_state.message:
                return health_state.message
            if health_state.activity:
                self.memory.current_activity = health_state.activity
        if self.memory.current_activity == "medicine":
                return await self.handle_medicine(query_dto)
        if self.memory.current_activity == "exercise":
                return await self.handle_exercise(query_dto)
        
    async def handle_medicine(self, query_dto: QueryDTO):
        logger.info("Handling medicine query", message=query_dto.message)
        messages = []
        messages.append(SystemMessage(content=medicine_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        response = await self.chat_llm.ainvoke(messages)
        logger.info("Generated medicine response", response=response)
        return response.content
        
    async def handle_exercise(self, query_dto: QueryDTO):
        logger.info("Handling exercise query", message=query_dto.message)
        if not self.memory.exercise_script:
            logger.debug("Generating new exercise script")
            messages = []
            messages.append(SystemMessage(content=exercise_script_prompt))
            messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
            messages.append(HumanMessage(content=query_dto.message))
            exercise_script = await self.exercise_script_llm.ainvoke(messages)
            self.memory.exercise_script = exercise_script.messages
            self.memory.script_index + 1
            logger.info("Created exercise script", script=exercise_script.messages)
            return exercise_script.messages[0]
        if self.memory.script_index < len(self.memory.exercise_script):
            logger.debug("Processing exercise step", 
                        script_index=self.memory.script_index,
                        total_steps=len(self.memory.exercise_script))
            messages = []
            messages.append(SystemMessage(content=excercise_prompt.format(exercise_script=self.construct_exercise_script(self.memory.exercise_script))))
            messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
            messages.append(HumanMessage(content=query_dto.message))
            self.memory.script_index += 1
            exercise_state = await self.exercise_llm.ainvoke(messages)
            logger.info("Exercise state updated", 
                       acknowledged=exercise_state.user_acknowledged,
                       message=exercise_state.message)
            if exercise_state.user_acknowledged:
                self.memory.script_index += 1
                return exercise_state.message
            else:
                return exercise_state.message
        else:
            logger.debug("Completing exercise routine")
            messages = []
            messages.append(SystemMessage(content=excercise_prompt.format(exercise_script= self.construct_exercise_script(self.memory.exercise_script))))
            messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
            messages.append(HumanMessage(content=query_dto.message))
            exercise_state = await self.exercise_llm.ainvoke(messages)
            return exercise_state.message

    def construct_exercise_script(self, exercise_script: List[str]):
        logger.debug("Constructing exercise script", script_length=len(exercise_script))
        return "\n".join(exercise_script)
