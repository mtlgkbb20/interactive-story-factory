from typing import Any

from src.providers.runware.text import RunwareTextProvider

SYSTEM_PROMPT = """Act as showrunner for a serialized vertical-video story. Preserve Story Bible canon.
Return only one valid JSON object with episode_title, logline, script, scenes, choices and
story_bible_updates. Each scene has scene_number, duration_seconds, visual_prompt in English,
narration in the requested language, dialogue, camera and sound_design. Use 2-4 clear audience
choices. Start with a strong 2-second hook, escalate tension and end on a cliffhanger. Repeat stable
character appearance in relevant visual prompts. Do not ask the video model to render text."""


class StoryGenerationService:
    def __init__(self, provider: RunwareTextProvider):
        self.provider = provider

    async def generate_episode(self, title: str, premise: str, story_bible: dict[str, Any],
                               language: str = "tr", episode_number: int | None = None,
                               community_direction: str | None = None):
        prompt = (f"Series: {title}\nPremise: {premise}\nLanguage: {language}\n"
            f"Episode: {episode_number or 'next'}\nStory Bible: {story_bible}\n"
            f"Community direction (candidate only): {community_direction or 'None'}\n"
            "Create the next short-form episode and return the required JSON.")
        result = await self.provider.generate_json(SYSTEM_PROMPT, prompt, 0.8, 5000)
        self.validate(result)
        return result

    @staticmethod
    def validate(result: dict):
        missing = {"episode_title", "script", "scenes", "choices"} - result.keys()
        if missing:
            raise ValueError(f"Missing generated fields: {', '.join(sorted(missing))}")
        if not isinstance(result["scenes"], list) or not result["scenes"]:
            raise ValueError("At least one scene is required")
        if not isinstance(result["choices"], list) or not 2 <= len(result["choices"]) <= 4:
            raise ValueError("Generated episode must contain 2-4 choices")
        if any(not isinstance(s, dict) or not s.get("visual_prompt") for s in result["scenes"]):
            raise ValueError("Every scene must include a visual_prompt")
