from deepgram import Deepgram
from app.django_orm import settings
class TranscriptionService:
    def __init__(self):
        self.deepgram = Deepgram(settings.DEEPGRAM_API_KEY)

    async def transcribe_audio(self, audio_data: bytes) -> str:
        source = {'buffer': audio_data, 'mimetype': 'audio/wav'}
        response = await self.deepgram.transcription.prerecorded(source, {
            'smart_format': True,
            'model': 'general',
        })
        return response['results']['channels'][0]['alternatives'][0]['transcript'] 