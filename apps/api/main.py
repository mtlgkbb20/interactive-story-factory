import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.community_engine.classifier import classify_comment
from src.community_engine.voting import tally_votes
from src.core.config import settings
from src.core.database import Base, engine, get_db
from src.core.models import Comment, Episode, Story
from src.providers.runware.client import RunwareClient, RunwareError
from src.providers.runware.text import RunwareTextProvider
from src.providers.runware.video import RunwareVideoProvider
from src.story_engine.generation import StoryGenerationService
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
                      voting_closes_at=datetime.now(UTC) + timedelta(hours=payload.voting_hours))
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



class EpisodeGenerate(BaseModel):
    language: str = "tr"
    episode_number: int | None = Field(default=None, ge=1)
    community_direction: str | None = Field(default=None, max_length=4000)
    voting_hours: int = Field(default=24, ge=1, le=168)


class VideoGenerate(BaseModel):
    prompt: str = Field(min_length=5, max_length=12000)
    model: str | None = None
    width: int | None = Field(default=None, ge=256, le=4096)
    height: int | None = Field(default=None, ge=256, le=4096)
    duration: int | None = Field(default=None, ge=1, le=30)
    inputs: dict | None = None


def runware_client() -> RunwareClient:
    if not settings.runware_api_key:
        raise HTTPException(status_code=503, detail="RUNWARE_API_KEY is not configured")
    return RunwareClient(settings.runware_api_key, settings.runware_base_url)


@app.post(f"{settings.api_prefix}/stories/{{story_id}}/episodes/generate", status_code=201)
async def generate_episode(story_id: str, payload: EpisodeGenerate,
                           db: Session = Depends(get_db),
                           client: RunwareClient = Depends(runware_client)):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        generated = await StoryGenerationService(RunwareTextProvider(client)).generate_episode(
            title=story.title, premise=story.premise, story_bible=story.story_bible,
            language=payload.language or story.language, episode_number=payload.episode_number,
            community_direction=payload.community_direction)
    except (RunwareError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    episode = Episode(story_id=story.id, title=generated["episode_title"],
        script=json.dumps(generated, ensure_ascii=False), choices=generated["choices"],
        status=EpisodeStatus.SCRIPTED.value,
        voting_closes_at=datetime.now(UTC) + timedelta(hours=payload.voting_hours))
    db.add(episode)
    db.commit()
    db.refresh(episode)
    result = episode.to_dict()
    result["generated"] = generated
    return result


@app.post(f"{settings.api_prefix}/media/video")
async def generate_video(payload: VideoGenerate,
                         client: RunwareClient = Depends(runware_client)):
    try:
        job = await RunwareVideoProvider(client).generate_scene(
            payload.prompt, model=payload.model, width=payload.width, height=payload.height,
            duration=payload.duration, inputs=payload.inputs)
    except (RunwareError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return job.__dict__


@app.get(f"{settings.api_prefix}/media/tasks/{{task_uuid}}")
async def get_media_task(task_uuid: str, client: RunwareClient = Depends(runware_client)):
    try:
        job = await RunwareVideoProvider(client).get_job(task_uuid)
    except RunwareError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return job.__dict__
