from openai import AsyncOpenAI
from app.core import settings
class AudioService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def text_to_speech(self, text: str) -> bytes:
        response = await self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        return response.read() 