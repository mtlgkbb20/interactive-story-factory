import json

from src.core.config import settings
from src.providers.runware.client import RunwareClient, RunwareError


def extract_json_object(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith(chr(96) * 3):
        cleaned = cleaned.split("\n", 1)[-1].removesuffix(chr(96) * 3).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise RunwareError("Text model did not return a JSON object")
    try:
        result = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise RunwareError(f"Invalid JSON from text model: {exc.msg}") from exc
    if not isinstance(result, dict):
        raise RunwareError("Text model response must be an object")
    return result


class RunwareTextProvider:
    def __init__(self, client: RunwareClient, model: str | None = None):
        self.client, self.model = client, model or settings.runware_text_model

    async def generate_json(self, system_prompt: str, user_prompt: str,
                            temperature: float = 0.7, max_tokens: int = 4000):
        response = await self.client.generate_text(self.model, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}], temperature, max_tokens)
        text = response.get("text")
        if not isinstance(text, str) or not text.strip():
            raise RunwareError("Runware text task returned no text")
        return extract_json_object(text)
