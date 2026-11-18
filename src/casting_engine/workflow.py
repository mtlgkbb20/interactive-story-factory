from enum import StrEnum


class CastingStatus(StrEnum):
    CANDIDATES_PENDING = "candidates_pending"
    AWAITING_SELECTION = "awaiting_selection"
    REFERENCES_PENDING = "references_pending"
    AWAITING_APPROVAL = "awaiting_approval"
    CAST_LOCKED = "cast_locked"
