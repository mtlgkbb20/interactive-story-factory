from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
