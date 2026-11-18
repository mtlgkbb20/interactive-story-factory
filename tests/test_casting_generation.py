import pytest

from src.casting_engine.generation import CastingDirector, CastingGenerationError

class FakeTextProvider:
    def __init__(self, result):
        self.result = result

    async def generate_json(self, *args, **kwargs):
        return self.result

def valid_role():
    return {
        "role_key": "protagonist", "display_name": "Protagonist",
        "narrative_function": "main character", "age_range": "28-32",
        "personality": "reserved", "physical_description": "short dark hair",
        "wardrobe": "simple dark jacket", "visual_style": "cinematic photorealism",
        "candidate_prompts": [f"portrait candidate {n}" for n in range(4)],
    }

@pytest.mark.asyncio
async def test_casting_director_accepts_valid_story_specific_roles():
    director = CastingDirector(FakeTextProvider({"roles": [valid_role(), {
        **valid_role(), "role_key": "stranger", "display_name": "Stranger"
    }]}))
    roles = await director.create_cast("The Contract", "A stranger offers a deal.")
    assert len(roles) == 2
    assert len(roles[0]["candidate_prompts"]) == 4

@pytest.mark.asyncio
async def test_casting_director_rejects_wrong_candidate_count():
    role = valid_role()
    role["candidate_prompts"] = ["only one"]
    director = CastingDirector(FakeTextProvider({"roles": [role, valid_role()]}))
    with pytest.raises(CastingGenerationError):
        await director.create_cast("The Contract", "A stranger offers a deal.")
