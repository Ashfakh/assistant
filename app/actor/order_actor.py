from typing import Optional

from pydantic import BaseModel
from app.actor.actor import Actor
from app.dto.message import MessageMemory
from app.dto.session import QueryDTO
from app.scripts.web_browse import WebBrowse
from app.services.chat_service import ChatService
from app.services.llm_factory import LLMFactory, LLMProvider
from langchain.schema import HumanMessage, SystemMessage
import structlog
import asyncio

logger = structlog.get_logger(__name__)


communication_prompt = """
        You are User's order assistant. Follow these guidelines:
        1. Order food from the restaurant
        2. Ask the user for the item and restaurant one by one and set it to the item, restaurant respectively
        2. you can ask the user question by setting the question to the query
        """

class OrderState(BaseModel):
    item: Optional[str] = None
    quantity: Optional[int] = None
    restaurant: Optional[str] = None
    query: Optional[str] = None


class OrderActor(Actor):
    def __init__(self, initial_memory: Optional[MessageMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        self.chat_service = ChatService()
        self.llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            structured_cls=OrderState
        )

    async def _on_receive(self, query_dto: QueryDTO):        
        messages = []
        messages.append(SystemMessage(content=communication_prompt))
        messages.extend(self.chat_service.create_messages(query_dto.session_dto.chat_history))
        messages.append(HumanMessage(content=query_dto.message))
        message_state = await self.llm.ainvoke(messages)
        if message_state.query:
            return message_state.query
        else:
            await self.handle_message(message_state, query_dto)
            return None
        
    async def handle_message(self, message_state: OrderState, query_dto: QueryDTO):
        logger.info("Message State", message_state=message_state)
        content_request = f"Order {message_state.item} with the quantity {message_state.quantity} from {message_state.restaurant}"
        web_browse = WebBrowse()
        prompt =  """Imagine you are a robot ordering food from Swiggy, just like humans. 
        Now you need to complete a task of ordering the food you can select the address as Home which says wework galaxy. In each iteration, you will receive an Observation that includes a screenshot of swiggy webpage
          and some texts. This screenshot will\nfeature Numerical Labels placed in the TOP LEFT corner of each Web Element. 
          Carefully analyze the visual\ninformation to identify the Numerical Label corresponding to the Web Element that requires interaction, 
          then follow\nthe guidelines and choose one of the following actions:\n\n
          1. Click a Web Element.\n
          2. Delete existing content in a textbox and then type content.\n
          3. Scroll up or down.\n
          4. Wait \n
          5. Go back\n
          6. Return to google to start over.\n
          7. Mark Goal as Success once the Google pay option is selected and the timer page is visible.\n\n
          Correspondingly, Action should STRICTLY follow the format:\n\n
          - Click [Numerical_Label] \n
          - Type [Numerical_Label]; [Content] \n
          - Scroll [Numerical_Label or WINDOW]; [up or down] \n
          - Wait \n
          - GoBack\n
          - Google\n
          - Goal [Success]\n\n
          Key Guidelines You MUST follow:\n\n* Action guidelines *\n
          1) Execute only one action per iteration.\n
          2) When clicking or typing, ensure to select the correct bounding box.\n
          3) Numeric labels lie in the top-left corner of their corresponding bounding boxes and are colored the same.\n\n
          * Web Browsing Guidelines *\n
          1) Don't interact with useless web elements like Login, Sign-in, donation that appear in Webpages\n
          2) Select strategically to minimize time wasted.\n
          3) If the order is placed, set Goal as Success\n\n
          Your reply should strictly follow the format:\n\n
          Thought: {{Your brief thoughts (briefly summarize the info that will help you achieve Goal)}}\n
          Action: {{One Action format you choose}}\n
          Then the User will provide:\n
          Observation: {{A labeled screenshot Given by User}}\n"""
        logger.info("sending message", message_state=message_state)
        await asyncio.create_task(web_browse.browse(content_request, "https://www.swiggy.com/search", prompt))
