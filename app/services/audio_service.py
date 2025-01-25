# from openai import AsyncOpenAI
from elevenlabs.client import ElevenLabs
from app.core import settings
import asyncio
from functools import partial

class AudioService:
    def __init__(self):
        # self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

    async def text_to_speech(self, text: str) -> bytes:
        # response = await self.client.audio.speech.create(
        #     model="tts-1",
        #     voice="alloy",
        #     input=text
        # )
        # return response.read()
        loop = asyncio.get_event_loop()
        audio_generator = await loop.run_in_executor(
            None,
            partial(
                self.client.generate,
                text=text,
                voice_id="WnFIhLMD7HtSxjuKKrfY",
                model="eleven_monolingual_v1"
            )
        )
        # Convert generator to bytes
        audio = b"".join(list(audio_generator))
        return audio 