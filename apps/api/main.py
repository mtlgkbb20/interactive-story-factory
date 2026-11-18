from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.community_engine.classifier import classify_comment
from src.community_engine.voting import tally_votes
from src.core.config import settings
from src.core.database import Base, engine, get_db
from src.core.models import Comment, Episode, Story
from src.story_engine.story_bible import empty_story_bible
from src.story_engine.workflow import EpisodeStatus


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    premise: str = Field(min_length=10, max_length=4000)
    language: str = "tr"


class EpisodeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    script: str = ""
    choices: list[str] = Field(min_length=2, max_length=4)
    voting_hours: int = Field(default=24, ge=1, le=168)


class CommentIngest(BaseModel):
    platform: str = Field(min_length=2, max_length=30)
    external_comment_id: str = Field(min_length=1, max_length=200)
    author_id: str | None = None
    text: str = Field(min_length=1, max_length=5000)


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.post(f"{settings.api_prefix}/stories", status_code=201)
def create_story(payload: StoryCreate, db: Session = Depends(get_db)):
    story = Story(title=payload.title, premise=payload.premise, language=payload.language,
                  story_bible=empty_story_bible(payload.title, payload.premise))
    db.add(story)
    db.commit()
    db.refresh(story)
    return story.to_dict()


@app.get(f"{settings.api_prefix}/stories")
def list_stories(db: Session = Depends(get_db)):
    stories = db.scalars(select(Story).order_by(Story.created_at.desc())).all()
    return [story.to_dict() for story in stories]


@app.post(f"{settings.api_prefix}/stories/{{story_id}}/episodes", status_code=201)
def create_episode(story_id: str, payload: EpisodeCreate, db: Session = Depends(get_db)):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    episode = Episode(story_id=story.id, title=payload.title, script=payload.script,
                      choices=payload.choices, status=EpisodeStatus.SCRIPTED.value,
                      voting_closes_at=datetime.now(timezone.utc) + timedelta(hours=payload.voting_hours))
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode.to_dict()


@app.get(f"{settings.api_prefix}/episodes/{{episode_id}}")
def get_episode(episode_id: str, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode.to_dict()


@app.post(f"{settings.api_prefix}/episodes/{{episode_id}}/comments", status_code=202)
def ingest_comment(episode_id: str, payload: CommentIngest, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    if episode.status not in {EpisodeStatus.PUBLISHED.value, EpisodeStatus.COLLECTING_COMMENTS.value}:
        raise HTTPException(status_code=409, detail="Episode is not collecting comments")
    existing = db.scalar(select(Comment).where(Comment.platform == payload.platform,
                            Comment.external_comment_id == payload.external_comment_id))
    if existing:
        return {"accepted": False, "reason": "duplicate_comment"}
    result = classify_comment(payload.text, episode.choices)
    db.add(Comment(episode_id=episode.id, platform=payload.platform,
                   external_comment_id=payload.external_comment_id, author_id=payload.author_id,
                   text=payload.text, classification=result.kind, selected_option=result.option))
    db.commit()
    return {"accepted": True, "classification": result.model_dump()}


@app.post(f"{settings.api_prefix}/episodes/{{episode_id}}/close-voting")
def close_voting(episode_id: str, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    if episode.status not in {EpisodeStatus.PUBLISHED.value, EpisodeStatus.COLLECTING_COMMENTS.value}:
        raise HTTPException(status_code=409, detail="Episode cannot close voting from current state")
    comments = db.scalars(select(Comment).where(Comment.episode_id == episode.id)).all()
    votes = [{"comment_id": c.external_comment_id, "author_id": c.author_id,
              "option": c.selected_option, "classification": c.classification} for c in comments]
    result = tally_votes(votes, episode.choices)
    episode.vote_result = result.model_dump()
    episode.status = EpisodeStatus.VOTING_CLOSED.value
    db.commit()
    return result.model_dump()
