from typing import Any

from src.providers.runware.text import RunwareTextProvider

ALLOWED_BIBLE_SECTIONS = {
    "relationships", "locations", "world_rules", "timeline", "character_arcs",
    "episode_summaries", "unresolved_threads", "next_arc",
}

REVISION_SYSTEM_PROMPT = """You are a meticulous showrunner revising an existing short-form serialized story.
Return exactly one JSON object with:
- title: concise story title, 1-180 characters
- premise: revised story premise, 10-4000 characters
- revision_summary: concise explanation of what changed
- affected_story_bible_sections: array using only relationships, locations, world_rules, timeline,
  episode_summaries, unresolved_threads, next_arc, character_arcs
- proposed_story_bible_updates: object containing only those same allowed section keys and proposed values.
Never include or modify the characters key, physical identities, physical descriptions, wardrobe,
casting selections, approved reference image URLs, or any media asset. Character motivation and arc changes may be proposed only under character_arcs. Do not regenerate episodes,
scenes, images, or narration. Preserve every story element not targeted by the user's scope and feedback.
When no Story Bible changes are necessary, return an empty array and empty object.
A revision is a proposal, not canon; clearly identify any affected sections rather than silently changing canon.
Respect the requested language for title and premise. Return valid JSON only."""


class StoryRevisionGenerationError(ValueError):
    pass


class StoryRevisionService:
    def __init__(self, provider: RunwareTextProvider):
        self.provider = provider

    async def revise(self, *, title: str, premise: str, story_bible: dict[str, Any],
                     feedback: str, scope: str, language: str = "tr") -> dict[str, Any]:
        prompt = (
            f"Current title: {title}\nCurrent premise: {premise}\nLanguage: {language}\n"
            f"Revision scope: {scope}\nUser feedback: {feedback}\n"
            f"Current Story Bible (read-only context): {story_bible}\n"
            "Return a revised story proposal and only necessary non-character Story Bible updates."
        )
        result = await self.provider.generate_json(
            REVISION_SYSTEM_PROMPT, prompt, temperature=0.75, max_tokens=3500
        )
        self.validate(result)
        return result

    @staticmethod
    def validate(result: dict[str, Any]) -> None:
        required = {
            "title", "premise", "revision_summary",
            "affected_story_bible_sections", "proposed_story_bible_updates",
        }
        missing = required - result.keys()
        if missing:
            raise StoryRevisionGenerationError(
                f"Missing generated fields: {', '.join(sorted(missing))}"
            )
        if not isinstance(result["title"], str) or not 1 <= len(result["title"].strip()) <= 180:
            raise StoryRevisionGenerationError("Generated title must contain 1-180 characters")
        if not isinstance(result["premise"], str) or not 10 <= len(result["premise"].strip()) <= 4000:
            raise StoryRevisionGenerationError("Generated premise must contain 10-4000 characters")
        if not isinstance(result["revision_summary"], str):
            raise StoryRevisionGenerationError("revision_summary must be a string")
        sections = result["affected_story_bible_sections"]
        updates = result["proposed_story_bible_updates"]
        if not isinstance(sections, list) or not isinstance(updates, dict):
            raise StoryRevisionGenerationError("Story Bible impact and updates must be structured")
        if any(section not in ALLOWED_BIBLE_SECTIONS for section in sections):
            raise StoryRevisionGenerationError("Unsupported or protected Story Bible section")
        if set(updates) - ALLOWED_BIBLE_SECTIONS:
            raise StoryRevisionGenerationError("Character and asset data cannot be revised by this workflow")
        if set(updates) - set(sections):
            raise StoryRevisionGenerationError("Every proposed update must be listed as affected")
