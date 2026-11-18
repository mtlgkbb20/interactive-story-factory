from enum import StrEnum


class EpisodeStatus(StrEnum):
    DRAFT = "draft"
    SCRIPTED = "scripted"
    VIDEO_GENERATED = "video_generated"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
    COLLECTING_COMMENTS = "collecting_comments"
    VOTING_CLOSED = "voting_closed"
    COMMENTS_ANALYZED = "comments_analyzed"
    NEXT_EPISODE_PLANNED = "next_episode_planned"
    FAILED = "failed"


ALLOWED_TRANSITIONS = {
    EpisodeStatus.DRAFT: {EpisodeStatus.SCRIPTED, EpisodeStatus.FAILED},
    EpisodeStatus.SCRIPTED: {EpisodeStatus.VIDEO_GENERATED, EpisodeStatus.FAILED},
    EpisodeStatus.VIDEO_GENERATED: {EpisodeStatus.AWAITING_APPROVAL, EpisodeStatus.FAILED},
    EpisodeStatus.AWAITING_APPROVAL: {EpisodeStatus.APPROVED, EpisodeStatus.FAILED},
    EpisodeStatus.APPROVED: {EpisodeStatus.PUBLISHED, EpisodeStatus.FAILED},
    EpisodeStatus.PUBLISHED: {EpisodeStatus.COLLECTING_COMMENTS},
    EpisodeStatus.COLLECTING_COMMENTS: {EpisodeStatus.VOTING_CLOSED, EpisodeStatus.FAILED},
    EpisodeStatus.VOTING_CLOSED: {EpisodeStatus.COMMENTS_ANALYZED},
    EpisodeStatus.COMMENTS_ANALYZED: {EpisodeStatus.NEXT_EPISODE_PLANNED},
    EpisodeStatus.NEXT_EPISODE_PLANNED: {EpisodeStatus.DRAFT},
    EpisodeStatus.FAILED: {EpisodeStatus.DRAFT},
}


def transition(current: EpisodeStatus | str, target: EpisodeStatus | str) -> EpisodeStatus:
    current_status, target_status = EpisodeStatus(current), EpisodeStatus(target)
    if target_status not in ALLOWED_TRANSITIONS[current_status]:
        raise ValueError(f"Invalid episode transition: {current_status} -> {target_status}")
    return target_status
