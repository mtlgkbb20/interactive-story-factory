from src.community_engine.classifier import classify_comment
from src.community_engine.voting import extract_vote, tally_votes


def test_single_explicit_vote():
    assert extract_vote("Kesinlikle A seçeneği", ["one", "two", "three"]) == "A"


def test_multiple_or_invalid_options_are_rejected():
    assert extract_vote("A mı B mi?", ["one", "two"]) is None
    assert extract_vote("C olsun", ["one", "two"]) is None


def test_free_text_is_not_a_vote():
    result = classify_comment("Bence karakterin bir kardeşi olsun", ["A", "B", "C"])
    assert result.kind == "story_suggestion"
    assert result.option is None


def test_vote_tally_deduplicates_author_and_ignores_feedback():
    result = tally_votes([
        {"comment_id": "1", "author_id": "u1", "option": "A", "classification": "vote"},
        {"comment_id": "2", "author_id": "u1", "option": "B", "classification": "vote"},
        {"comment_id": "3", "author_id": "u2", "option": "A", "classification": "vote"},
        {"comment_id": "4", "author_id": "u3", "option": None, "classification": "story_suggestion"},
    ], ["one", "two"])
    assert result.valid_votes == 2
    assert result.duplicate_votes == 1
    assert result.percentages["A"] == 100.0


def test_missing_identity_is_reported():
    result = tally_votes([{"comment_id": "1", "author_id": None, "option": "A",
                           "classification": "vote"}], ["one", "two"])
    assert result.identity_limitations
