from dataclasses import dataclass
from typing import Any

from src.core.config import settings
from src.providers.base import VideoProvider
from src.providers.runware.client import RunwareClient


@dataclass
class RunwareVideoJob:
    provider: str
    model: str
    task_uuid: str
    status: str
    progress: int | None = None
    asset_uri: str | None = None
    cost_usd: float | None = None
    metadata: dict[str, Any] | None = None


class RunwareVideoProvider(VideoProvider):
    def __init__(self, client: RunwareClient, model: str | None = None):
        self.client, self.model = client, model or settings.runware_video_model

    async def generate_scene(self, prompt: str, **kwargs: Any):
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        result = await self.client.submit_video(
            model=kwargs.get("model") or self.model, prompt=prompt,
            width=int(kwargs.get("width") or settings.runware_video_width),
            height=int(kwargs.get("height") or settings.runware_video_height),
            duration=int(kwargs.get("duration") or settings.runware_video_duration),
            inputs=kwargs.get("inputs"))
        return self.to_job(result)

    async def get_job(self, task_uuid: str):
        return self.to_job(await self.client.get_response(task_uuid))

    @staticmethod
    def to_job(result: dict[str, Any]):
        return RunwareVideoJob("runware", str(result.get("model", "configured")),
            result.get("taskUUID", ""), result.get("status", "success" if result.get("videoURL")
            else "processing"), result.get("progress"), result.get("videoURL"),
            result.get("cost"), {k:v for k,v in result.items()
            if k not in {"videoURL", "taskUUID", "cost"}})
