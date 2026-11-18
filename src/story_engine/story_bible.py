from typing import Any


def empty_story_bible(title: str, premise: str) -> dict[str, Any]:
    return {"title": title, "premise": premise, "canon_version": 1, "characters": [],
            "relationships": [], "locations": [], "world_rules": [], "timeline": [],
            "episode_summaries": [], "unresolved_threads": [], "community_ideas": [],
            "rejected_ideas": [], "next_arc": None}


def append_community_idea(bible: dict[str, Any], *, text: str, category: str,
                          source_episode_id: str, relevance_score: float) -> dict[str, Any]:
    if not 0 <= relevance_score <= 1:
        raise ValueError("relevance_score must be between 0 and 1")
    updated = dict(bible)
    ideas = list(updated.get("community_ideas", []))
    ideas.append({"text": text, "category": category, "source_episode_id": source_episode_id,
                  "relevance_score": relevance_score, "status": "candidate"})
    updated["community_ideas"] = ideas
    updated["canon_version"] = int(updated.get("canon_version", 1)) + 1
    return updated