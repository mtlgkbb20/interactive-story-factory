import json

import httpx
import pytest

from src.providers.runware.client import RunwareClient
from src.providers.runware.text import RunwareTextProvider, extract_json_object
from src.providers.runware.video import RunwareVideoProvider


@pytest.mark.asyncio
async def test_text_inference():
    seen = {}

    def handler(request):
        seen["task"] = json.loads(request.content)[0]
        return httpx.Response(200, json={"data":[{"taskType":"textInference",
            "text":'{"episode_title":"Pilot","script":"Hi","scenes":[{"visual_prompt":"Street"}],'
                   '"choices":["A","B"]}'}]})
    client = RunwareClient("key", transport=httpx.MockTransport(handler))
    result = await RunwareTextProvider(client, "test:text@1").generate_json("sys", "user")
    assert result["episode_title"] == "Pilot"
    assert seen["task"]["taskType"] == "textInference"


@pytest.mark.asyncio
async def test_async_video_job_and_poll():
    tasks = []

    def handler(request):
        task = json.loads(request.content)[0]
        tasks.append(task)
        row = {"taskType":"videoInference","taskUUID":task["taskUUID"],"status":"processing"}
        if task["taskType"] == "getResponse":
            row.update(status="success", videoURL="https://example.test/clip.mp4", cost=0.12)
        return httpx.Response(200, json={"data":[row]})
    client = RunwareClient("key", transport=httpx.MockTransport(handler))
    provider = RunwareVideoProvider(client, "test:video@1")
    pending = await provider.generate_scene("cinematic alley", duration=5)
    complete = await provider.get_job(pending.task_uuid)
    assert pending.status == "processing"
    assert complete.asset_uri == "https://example.test/clip.mp4"
    assert tasks[0]["deliveryMethod"] == "async"
    assert tasks[1]["taskType"] == "getResponse"


def test_json_parser():
    fence = chr(96) * 3
    assert extract_json_object(fence + 'json\n{"ok":true}\n' + fence) == {"ok": True}
