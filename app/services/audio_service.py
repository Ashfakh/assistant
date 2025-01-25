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
                f"{self.base_url}/text-to-speech/C2RGMrNBTZaNfddRPeRH",
                headers=headers,
                json=data
            )
        )
        
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"ElevenLabs API error: {response.text}")

    async def text_to_speech_sarvam(self, text: str, target_language_code: str = "hi-IN") -> bytes:
        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": settings.SARVAM_API_KEY
        }
        
        data = {
            "inputs": [text],
            "target_language_code": target_language_code,
            "speaker": "meera",
            "pitch": 0,
            "pace": 1.65,
            "loudness": 1.5,
            "speech_sample_rate": 8000,
            "enable_preprocessing": False,
            "model": "bulbul:v1",
            "eng_interpolation_wt": 123,
            "override_triplets": {}
        }

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                "https://api.sarvam.ai/text-to-speech",
                headers=headers,
                json=data
            )
        )
        
        if response.status_code == 200:
            response_data = response.json()
            # The API returns a list of audio strings, we'll take the first one
            return response_data["audios"][0].encode()
        else:
            raise Exception(f"Sarvam.ai API error: {response.text}") 