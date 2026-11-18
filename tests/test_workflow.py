import pytest

from src.story_engine.workflow import EpisodeStatus, transition


def test_human_approval_required_before_publishing():
    assert transition(EpisodeStatus.VIDEO_GENERATED, EpisodeStatus.AWAITING_APPROVAL)
    with pytest.raises(ValueError):
        transition(EpisodeStatus.AWAITING_APPROVAL, EpisodeStatus.PUBLISHED)


def test_published_episode_can_collect_comments():
    assert transition(EpisodeStatus.PUBLISHED, EpisodeStatus.COLLECTING_COMMENTS)


def test_invalid_transition_rejected():
    with pytest.raises(ValueError):
        transition(EpisodeStatus.DRAFT, EpisodeStatus.PUBLISHED)
