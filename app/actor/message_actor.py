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
        You are User's communication assistant. Follow these guidelines:
        1. Handle calls, messages, and updates.
        2. Always confirm message content before sending and who to send it to
        3. Maintain conversation context with family members
        4. once you've confirmed the message, set it to message_to_sent
        5. set the recipient to the person you've confirmed
        6. If you have any questions, ask them by setting the the question to query
        Current Communication Context:
        Missed Calls: 2 calls from Rahul (son) this morning
        Family Updates: Rohit planning to visit today
        Upcoming Events: Nirvi's 4th birthday tomorrow
        """

class MessageState(BaseModel):
    message_to_sent: Optional[str] = None
    recipient: Optional[str] = None
    query: Optional[str] = None


class MessageActor(Actor):
    def __init__(self, initial_memory: Optional[MessageMemory], actor_id: str = None):
        super().__init__(initial_memory, actor_id)
        self.chat_service = ChatService()
        self.llm = LLMFactory.get_chat_llm(
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            structured_cls=MessageState
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
        
    async def handle_message(self, message_state: MessageState, query_dto: QueryDTO):
        logger.info("Message State", message_state=message_state)
        content_request = f"Send a message to {message_state.recipient} with the content {message_state.message_to_sent} on whatsapp"
        web_browse = WebBrowse()
        prompt =  """Imagine you are a robot sending a message through whatsapp web, just like humans. 
        Now you need to complete a task of sending the message. In each iteration, you will receive an Observation that includes a screenshot of whatsapp webpage
          and some texts. This screenshot will\nfeature Numerical Labels placed in the TOP LEFT corner of each Web Element. 
          Carefully analyze the visual\ninformation to identify the Numerical Label corresponding to the Web Element that requires interaction, 
          then follow\nthe guidelines and choose one of the following actions:\n\n
          1. Click a Web Element.\n
          2. Delete existing content in a textbox and then type content.\n
          3. Scroll up or down.\n
          4. Wait \n
          5. Go back\n
          6. Return to google to start over.\n7. Mark Goal as Success.\n\n
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
          3) If the Task is to play a youtube video, If the video page is open, set Goal as Success. 
          If your task is to send a message, once the message is send and it is visible to the user on the chat box, set Goal as Success\n\n
          Your reply should strictly follow the format:\n\n
          Thought: {{Your brief thoughts (briefly summarize the info that will help you achieve Goal)}}\n
          Action: {{One Action format you choose}}\n
          Then the User will provide:\n
          Observation: {{A labeled screenshot Given by User}}\n"""
        logger.info("sending message", message_state=message_state)
        asyncio.create_task(web_browse.browse(content_request, "https://web.whatsapp.com", prompt))
