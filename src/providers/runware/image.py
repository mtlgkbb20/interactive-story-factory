from src.core.config import settings
from src.providers.runware.client import RunwareClient, RunwareError

class RunwareImageProvider:
    """Synchronous image generation adapter; returns provider URLs and metadata."""

    def __init__(self, client: RunwareClient, model: str | None = None):
        self.client = client
        self.model = model or settings.runware_image_model

    async def generate(self, prompt: str, reference_images: list[str] | None = None,
                       width: int = 1024, height: int = 1536) -> dict:
        task = {
            "taskType": "imageInference",
            "model": self.model,
            "positivePrompt": prompt,
            "width": width,
            "height": height,
            "numberResults": 1,
            "deliveryMethod": "sync",
            "includeCost": True,
        }
        if reference_images:
            task["inputs"] = {"referenceImages": reference_images}
        result = await self.client.request(task)
        image_url = result.get("imageURL")
        if not isinstance(image_url, str) or not image_url.startswith(("https://", "http://")):
            raise RunwareError("Runware image task returned no valid imageURL")
        return {"image_url": image_url, "image_uuid": result.get("imageUUID"),
                "task_uuid": result.get("taskUUID"), "cost": result.get("cost"),
                "model": result.get("model", self.model)}
