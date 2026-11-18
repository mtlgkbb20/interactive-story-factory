from typing import Any
from uuid import uuid4

import httpx


class RunwareError(RuntimeError):
    pass


class RunwareClient:
    def __init__(self, api_key: str, base_url: str = "https://api.runware.ai/v1",
                 timeout: float = 180.0, transport: httpx.AsyncBaseTransport | None = None):
        if not api_key:
            raise ValueError("RUNWARE_API_KEY is required")
        self.api_key, self.base_url = api_key, base_url.rstrip("/")
        self.timeout, self.transport = timeout, transport

    async def request(self, task: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(self.base_url, headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"}, json=[task])
        response.raise_for_status()
        payload = response.json()
        rows = payload if isinstance(payload, list) else payload.get("data", [])
        errors = [] if isinstance(payload, list) else payload.get("errors", [])
        if errors:
            err = errors[0]
            raise RunwareError(f"Runware error {err.get('code')}: {err.get('message')}")
        if not rows:
            raise RunwareError("Runware returned an empty response")
        return rows[0]

    async def generate_text(self, model: str, messages: list[dict[str, str]],
                            temperature: float = 0.7, max_tokens: int = 3000):
        return await self.request({"taskType": "textInference", "taskUUID": str(uuid4()),
            "model": model, "messages": messages, "settings": {"temperature": temperature,
            "maxTokens": max_tokens}, "includeCost": True})

    async def submit_video(self, model: str, prompt: str, width: int, height: int,
                           duration: int, inputs: dict | None = None):
        task = {"taskType": "videoInference", "taskUUID": str(uuid4()), "model": model,
            "positivePrompt": prompt, "width": width, "height": height, "duration": duration,
            "deliveryMethod": "async", "includeCost": True}
        if inputs:
            task["inputs"] = inputs
        return await self.request(task)

    async def get_response(self, task_uuid: str):
        return await self.request({"taskType": "getResponse", "taskUUID": task_uuid})
