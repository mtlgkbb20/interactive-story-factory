import httpx

from src.core.config import settings
from src.providers.base import TextToSpeechProvider


class ElevenLabsClient(TextToSpeechProvider):
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str | None = None, model_id: str | None = None):
        self.api_key = api_key or settings.elevenlabs_api_key
        self.model_id = model_id or settings.elevenlabs_model_id
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY is required")

    async def synthesize(self, text: str, voice_id: str, *, stability: float = 0.5,
                         similarity_boost: float = 0.75,
                         output_format: str = "mp3_44100_128") -> bytes:
        if not text.strip() or not voice_id.strip():
            raise ValueError("text and voice_id must not be empty")
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.BASE_URL}/text-to-speech/{voice_id}",
                params={"output_format": output_format},
                headers={"xi-api-key": self.api_key, "accept": "audio/mpeg"},
                json={"text": text, "model_id": self.model_id,
                      "voice_settings": {"stability": stability,
                                         "similarity_boost": similarity_boost}},
            )
            response.raise_for_status()
            return response.content
