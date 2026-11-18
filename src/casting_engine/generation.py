import json
from typing import Any

from src.providers.runware.image import RunwareImageProvider
from src.providers.runware.text import RunwareTextProvider

CASTING_SYSTEM_PROMPT = """You are a casting director for a cinematic short-form episodic story.
Analyze the story premise and return only valid JSON with a 'roles' array. Create 2-6
story-specific character roles. Each role must contain role_key (stable snake_case identifier),
display_name, narrative_function, age_range, personality, physical_description, wardrobe,
visual_style, and candidate_prompts (exactly 4 distinct English portrait prompts).
Prompts must depict the same role concept with meaningfully different faces/appearances,
not four copies. Use a consistent art direction across all candidates: cinematic photorealism,
vertical portrait, chest-up framing, neutral uncluttered studio background, natural skin texture,
clear unobstructed face, no text, no watermark. Do not cast real public figures. Keep age ranges
appropriate and do not sexualize characters. The role descriptions must fit the supplied genre,
period, tone and premise. Do not invent unnecessary roles."""

class CastingGenerationError(ValueError):
    pass

class CastingDirector:
    def __init__(self, text_provider: RunwareTextProvider):
        self.text_provider = text_provider

    async def create_cast(self, title: str, premise: str, genre: str | None = None,
                          period: str | None = None, tone: str | None = None,
                          language: str = "tr") -> list[dict[str, Any]]:
        prompt = (
            f"Story: {title}\nPremise: {premise}\nGenre: {genre or 'infer from premise'}\n"
            f"Period: {period or 'modern unless premise says otherwise'}\n"
            f"Tone: {tone or 'infer from premise'}\nLanguage: {language}\n"
            "Design the story-specific cast and four visually distinct candidates per role."
        )
        result = await self.text_provider.generate_json(CASTING_SYSTEM_PROMPT, prompt, 0.7, 5000)
        roles = result.get("roles")
        if not isinstance(roles, list) or not 2 <= len(roles) <= 6:
            raise CastingGenerationError("Casting response must contain 2-6 roles")
        seen = set()
        for role in roles:
            required = {"role_key", "display_name", "narrative_function", "age_range",
                        "personality", "physical_description", "wardrobe", "visual_style",
                        "candidate_prompts"}
            if not isinstance(role, dict) or required - role.keys():
                raise CastingGenerationError("A casting role is missing required fields")
            key = role["role_key"]
            prompts = role["candidate_prompts"]
            if not isinstance(key, str) or not key or key in seen:
                raise CastingGenerationError("Role keys must be unique non-empty strings")
            seen.add(key)
            if not isinstance(prompts, list) or len(prompts) != 4 or not all(
                isinstance(item, str) and item.strip() for item in prompts
            ):
                raise CastingGenerationError("Each role must have exactly four candidate prompts")
        return roles

class CandidateImageService:
    def __init__(self, provider: RunwareImageProvider):
        self.provider = provider

    async def generate(self, prompts: list[str]) -> list[dict[str, Any]]:
        results = []
        for prompt in prompts:
            results.append(await self.provider.generate(prompt))
        return results
