import re

from pydantic import BaseModel


class CommentClassification(BaseModel):
    kind: str
    option: str | None = None
    confidence: float
    rationale: str


def classify_comment(text: str, choices: list[str]) -> CommentClassification:
    allowed = {chr(ord("A") + i) for i in range(len(choices))}
    found = {m.group(1).upper() for m in re.finditer(
        r"(?<![A-Za-z0-9])([A-D])(?![A-Za-z0-9])", text, re.I)} & allowed
    if len(found) == 1:
        return CommentClassification(kind="vote", option=found.pop(), confidence=0.98,
                                     rationale="Exactly one valid option letter was found.")
    if len(found) > 1:
        return CommentClassification(kind="ambiguous", confidence=0.95,
                                     rationale="Multiple option letters were found.")
    lower = text.casefold()
    if any(word in lower for word in ("şikayet", "çok kısa", "ses kötü", "altyazı")):
        kind = "production_feedback"
    elif any(word in lower for word in ("bence", "teori", "aslında", "çıksın", "olsun")):
        kind = "story_suggestion"
    elif "?" in text:
        kind = "question"
    else:
        kind = "general_feedback"
    return CommentClassification(kind=kind, confidence=0.55,
                                 rationale="No single explicit vote; routed as free-form feedback.")