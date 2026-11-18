import pytest

from src.story_engine.revision import StoryRevisionGenerationError, StoryRevisionService


class FakeTextProvider:
    def __init__(self, result):
        self.result = result

    async def generate_json(self, *args, **kwargs):
        return self.result


def valid_revision():
    return {
        "title": "The Last Contract",
        "premise": "A stranger offers a contract with a hidden and irreversible cost.",
        "revision_summary": "The premise now has a more distinctive central cost.",
        "affected_story_bible_sections": ["world_rules"],
        "proposed_story_bible_updates": {"world_rules": ["Every promise has a visible cost."]},
    }


@pytest.mark.asyncio
async def test_story_revision_returns_valid_proposal_without_mutating_inputs():
    original_bible = {"characters": [{"name": "Mira", "reference_image_url": "keep.png"}]}
    service = StoryRevisionService(FakeTextProvider(valid_revision()))
    result = await service.revise(
        title="Old title", premise="An old premise with enough characters.",
        story_bible=original_bible, feedback="Make it less predictable.",
        scope="whole_story",
    )
    assert result["title"] == "The Last Contract"
    assert original_bible["characters"][0]["reference_image_url"] == "keep.png"


@pytest.mark.asyncio
async def test_story_revision_rejects_character_or_asset_mutations():
    result = valid_revision()
    result["proposed_story_bible_updates"] = {"characters": [{"name": "Changed"}]}
    result["affected_story_bible_sections"] = ["characters"]
    service = StoryRevisionService(FakeTextProvider(result))
    with pytest.raises(StoryRevisionGenerationError):
        await service.revise(
            title="Old", premise="An old premise with enough characters.",
            story_bible={}, feedback="Change the cast.", scope="characters",
        )


@pytest.mark.asyncio
async def test_story_revision_rejects_unlisted_bible_updates():
    result = valid_revision()
    result["affected_story_bible_sections"] = []
    service = StoryRevisionService(FakeTextProvider(result))
    with pytest.raises(StoryRevisionGenerationError):
        await service.revise(
            title="Old", premise="An old premise with enough characters.",
            story_bible={}, feedback="Change the rules.", scope="whole_story",
        )
