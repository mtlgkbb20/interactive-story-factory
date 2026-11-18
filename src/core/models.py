from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Story(Base):
    __tablename__ = "stories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(180))
    premise: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(12), default="tr")
    story_bible: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "premise": self.premise,
                "language": self.language, "story_bible": self.story_bible,
                "created_at": self.created_at.isoformat()}


class Episode(Base):
    __tablename__ = "episodes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    script: Mapped[str] = mapped_column(Text, default="")
    choices: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="scripted", index=True)
    vote_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    voting_closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {"id": self.id, "story_id": self.story_id, "title": self.title,
                "script": self.script, "choices": self.choices, "status": self.status,
                "vote_result": self.vote_result,
                "voting_closes_at": self.voting_closes_at.isoformat() if self.voting_closes_at else None,
                "created_at": self.created_at.isoformat()}


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("platform", "external_comment_id",
                                       name="uq_platform_external_comment"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(30))
    external_comment_id: Mapped[str] = mapped_column(String(200))
    author_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(40), index=True)
    selected_option: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class CastingSession(Base):
    __tablename__ = "casting_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="candidates_pending", index=True)
    creative_brief: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self, roles: list) -> dict:
        return {"id": self.id, "story_id": self.story_id, "status": self.status,
                "creative_brief": self.creative_brief,
                "roles": roles,
                "created_at": self.created_at.isoformat()}


class CharacterRole(Base):
    __tablename__ = "casting_roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    casting_session_id: Mapped[str] = mapped_column(
        ForeignKey("casting_sessions.id", ondelete="CASCADE"), index=True)
    role_key: Mapped[str] = mapped_column(String(80))
    display_name: Mapped[str] = mapped_column(String(120))
    role_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    selected_candidate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reference_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_approved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self, candidates: list | None = None) -> dict:
        return {"id": self.id, "role_key": self.role_key, "display_name": self.display_name,
                "role_definition": self.role_definition,
                "selected_candidate_id": self.selected_candidate_id,
                "reference_image_url": self.reference_image_url,
                "reference_approved": self.reference_approved,
                "candidates": [candidate.to_dict() for candidate in (candidates or [])]}


class CharacterCandidate(Base):
    __tablename__ = "character_candidates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    role_id: Mapped[str] = mapped_column(ForeignKey("casting_roles.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(Text)
    image_uuid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    cost: Mapped[str | None] = mapped_column(String(40), nullable=True)
    selected: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {"id": self.id, "prompt": self.prompt, "image_url": self.image_url,
                "image_uuid": self.image_uuid, "provider_model": self.provider_model,
                "cost": self.cost, "selected": self.selected,
                "created_at": self.created_at.isoformat()}


class StoryRevision(Base):
    __tablename__ = "story_revisions"
    __table_args__ = (UniqueConstraint("story_id", "version", name="uq_story_revision_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column()
    scope: Mapped[str] = mapped_column(String(40))
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    premise: Mapped[str] = mapped_column(Text)
    story_bible_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    affected_story_bible_sections: Mapped[list] = mapped_column(JSON, default=list)
    proposed_story_bible_updates: Mapped[dict] = mapped_column(JSON, default=dict)
    revision_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="pending_approval", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "story_id": self.story_id, "version": self.version,
            "scope": self.scope, "feedback": self.feedback, "title": self.title,
            "premise": self.premise, "story_bible_snapshot": self.story_bible_snapshot,
            "affected_story_bible_sections": self.affected_story_bible_sections,
            "proposed_story_bible_updates": self.proposed_story_bible_updates,
            "revision_summary": self.revision_summary, "status": self.status,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }
