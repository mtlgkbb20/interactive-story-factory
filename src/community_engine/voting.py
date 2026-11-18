import re
from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

OPTION_PATTERN = re.compile(r"(?<![A-Za-z0-9])([A-D])(?![A-Za-z0-9])", re.IGNORECASE)


class VoteTally(BaseModel):
    valid_votes: int
    invalid_or_ambiguous: int
    duplicate_votes: int
    counts: dict[str, int]
    percentages: dict[str, float]
    winner: str | None
    identity_limitations: list[str] = Field(default_factory=list)


def extract_vote(text: str, options: list[str]) -> str | None:
    allowed = {chr(ord("A") + i) for i in range(len(options))}
    selected = {m.group(1).upper() for m in OPTION_PATTERN.finditer(text)} & allowed
    return selected.pop() if len(selected) == 1 else None


def tally_votes(votes: list[dict[str, Any]], options: list[str]) -> VoteTally:
    labels = [chr(ord("A") + i) for i in range(len(options))]
    counts: Counter[str] = Counter({label: 0 for label in labels})
    seen_comments: set[str] = set()
    seen_authors: set[str] = set()
    invalid = duplicates = 0
    identity_missing = False
    for vote in votes:
        if vote.get("classification") != "vote" or vote.get("option") not in labels:
            invalid += 1
            continue
        comment_id = str(vote.get("comment_id") or "")
        if not comment_id or comment_id in seen_comments:
            duplicates += 1
            continue
        seen_comments.add(comment_id)
        author = vote.get("author_id")
        if author:
            if str(author) in seen_authors:
                duplicates += 1
                continue
            seen_authors.add(str(author))
        else:
            identity_missing = True
        counts[vote["option"]] += 1
    total = sum(counts.values())
    percentages = {k: round(counts[k] * 100 / total, 2) if total else 0.0 for k in labels}
    maximum = max(counts.values(), default=0)
    winners = [k for k, v in counts.items() if v == maximum and v > 0]
    limitations = (["Missing author IDs mean one-person-one-vote cannot be guaranteed."]
                   if identity_missing else [])
    return VoteTally(valid_votes=total, invalid_or_ambiguous=invalid, duplicate_votes=duplicates,
                     counts=dict(counts), percentages=percentages,
                     winner=winners[0] if len(winners) == 1 else None,
                     identity_limitations=limitations)