from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class GeneratedAsset:
    provider: str
    model: str
    asset_uri: str
    duration_seconds: float | None = None
    cost_usd: float | None = None
    metadata: dict[str, Any] | None = None


class VideoProvider(ABC):
    @abstractmethod
    async def generate_scene(self, prompt: str, **kwargs: Any) -> GeneratedAsset:
        """Generate a clip using a provider-specific prompt adapter."""


class TextToSpeechProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, **kwargs: Any) -> bytes:
        """Return encoded speech audio."""