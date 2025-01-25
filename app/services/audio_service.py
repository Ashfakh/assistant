# from openai import AsyncOpenAI
import requests
from app.core import settings
import asyncio

class AudioService:
    def __init__(self):
        # self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"

    async def text_to_speech(self, text: str) -> bytes:
        # response = await self.client.audio.speech.create(
        #     model="tts-1",
        #     voice="alloy",
        #     input=text
        # )
        # return response.read()
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.75,
                "speaking_rate": 0.5,  # 0.5 is slower, 1.0 is normal, 2.0 is faster
                "style": 0.0
            }
        }

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{self.base_url}/text-to-speech/21m00Tcm4TlvDq8ikWAM",
                headers=headers,
                json=data
            )
        )
        
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"ElevenLabs API error: {response.text}") 