import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.casting_engine.generation import CastingDirector, CastingGenerationError
from src.casting_engine.workflow import CastingStatus
from src.community_engine.classifier import classify_comment
from src.community_engine.voting import tally_votes
from src.core.config import settings
from src.core.database import Base, engine, get_db
from src.core.models import (
    CastingSession,
    CharacterCandidate,
    CharacterRole,
    Comment,
    Episode,
    Story,
)
from src.providers.runware.client import RunwareClient, RunwareError
from src.providers.runware.image import RunwareImageProvider
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


class CastingCreate(BaseModel):
    genre: str | None = Field(default=None, max_length=100)
    period: str | None = Field(default=None, max_length=100)
    tone: str | None = Field(default=None, max_length=300)
    language: str = "tr"


class CandidateSelect(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=36)


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
    latest_casting = db.scalar(select(CastingSession).where(
        CastingSession.story_id == story.id
    ).order_by(CastingSession.created_at.desc()))
    if latest_casting is None or latest_casting.status != CastingStatus.CAST_LOCKED.value:
        raise HTTPException(status_code=409,
            detail="Complete and approve story casting before generating an episode")
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



def get_casting_roles(db: Session, session_id: str):
    return db.scalars(select(CharacterRole).where(
        CharacterRole.casting_session_id == session_id
    ).order_by(CharacterRole.created_at)).all()


def serialize_casting(db: Session, session: CastingSession):
    roles = get_casting_roles(db, session.id)
    result = []
    for role in roles:
        candidates = db.scalars(select(CharacterCandidate).where(
            CharacterCandidate.role_id == role.id
        ).order_by(CharacterCandidate.created_at)).all()
        result.append(role.to_dict(candidates))
    return session.to_dict(result)


@app.post(f"{settings.api_prefix}/stories/{{story_id}}/casting", status_code=201)
async def create_casting(story_id: str, payload: CastingCreate,
                         db: Session = Depends(get_db),
                         client: RunwareClient = Depends(runware_client)):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        roles = await CastingDirector(RunwareTextProvider(client)).create_cast(
            title=story.title, premise=story.premise, genre=payload.genre,
            period=payload.period, tone=payload.tone, language=payload.language)
    except (RunwareError, CastingGenerationError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Casting generation failed: {exc}") from exc
    session = CastingSession(story_id=story.id,
        status=CastingStatus.CANDIDATES_PENDING.value,
        creative_brief={"genre": payload.genre, "period": payload.period,
                        "tone": payload.tone, "language": payload.language})
    db.add(session)
    db.flush()
    for definition in roles:
        db.add(CharacterRole(casting_session_id=session.id,
            role_key=definition["role_key"], display_name=definition["display_name"],
            role_definition=definition))
    db.commit()
    db.refresh(session)
    return serialize_casting(db, session)


@app.get(f"{settings.api_prefix}/casting/{{session_id}}")
def get_casting(session_id: str, db: Session = Depends(get_db)):
    session = db.get(CastingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Casting session not found")
    return serialize_casting(db, session)


@app.post(f"{settings.api_prefix}/casting/{{session_id}}/roles/{{role_id}}/candidates")
async def generate_role_candidates(session_id: str, role_id: str,
                                   db: Session = Depends(get_db),
                                   client: RunwareClient = Depends(runware_client)):
    session = db.get(CastingSession, session_id)
    role = db.get(CharacterRole, role_id)
    if session is None or role is None or role.casting_session_id != session_id:
        raise HTTPException(status_code=404, detail="Casting session or role not found")
    if session.status == CastingStatus.CAST_LOCKED.value:
        raise HTTPException(status_code=409, detail="Locked cast cannot be modified")
    prompts = role.role_definition.get("candidate_prompts", [])
    if len(prompts) != 4:
        raise HTTPException(status_code=409, detail="Role does not have four valid candidate prompts")
    try:
        provider = RunwareImageProvider(client)
        generated = []
        for prompt in prompts:
            generated.append(await provider.generate(prompt))
    except (RunwareError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Candidate image generation failed: {exc}") from exc
    # Regeneration preserves previous candidate records but invalidates this role's current selection.
    role.selected_candidate_id = None
    role.reference_image_url = None
    role.reference_approved = False
    previous_candidates = db.scalars(select(CharacterCandidate).where(
        CharacterCandidate.role_id == role.id)).all()
    for previous in previous_candidates:
        previous.selected = False
    for prompt, asset in zip(prompts, generated, strict=True):
        db.add(CharacterCandidate(role_id=role.id, prompt=prompt,
            image_url=asset["image_url"], image_uuid=asset.get("image_uuid"),
            provider_model=asset.get("model"),
            cost=str(asset["cost"]) if asset.get("cost") is not None else None))
    session.status = CastingStatus.AWAITING_SELECTION.value
    db.commit()
    return serialize_casting(db, session)


@app.post(f"{settings.api_prefix}/casting/{{session_id}}/roles/{{role_id}}/select")
def select_role_candidate(session_id: str, role_id: str, payload: CandidateSelect,
                          db: Session = Depends(get_db)):
    session = db.get(CastingSession, session_id)
    role = db.get(CharacterRole, role_id)
    if session is None or role is None or role.casting_session_id != session_id:
        raise HTTPException(status_code=404, detail="Casting session or role not found")
    if session.status == CastingStatus.CAST_LOCKED.value:
        raise HTTPException(status_code=409, detail="Locked cast cannot be modified")
    candidate = db.get(CharacterCandidate, payload.candidate_id)
    if candidate is None or candidate.role_id != role.id:
        raise HTTPException(status_code=404, detail="Candidate does not belong to this role")
    candidates = db.scalars(select(CharacterCandidate).where(
        CharacterCandidate.role_id == role.id)).all()
    for item in candidates:
        item.selected = item.id == candidate.id
    role.selected_candidate_id = candidate.id
    role.reference_image_url = None
    role.reference_approved = False
    session.status = CastingStatus.REFERENCES_PENDING.value
    db.commit()
    return serialize_casting(db, session)


@app.post(f"{settings.api_prefix}/casting/{{session_id}}/roles/{{role_id}}/reference")
def approve_role_reference(session_id: str, role_id: str, db: Session = Depends(get_db)):
    session = db.get(CastingSession, session_id)
    role = db.get(CharacterRole, role_id)
    if session is None or role is None or role.casting_session_id != session_id:
        raise HTTPException(status_code=404, detail="Casting session or role not found")
    if session.status == CastingStatus.CAST_LOCKED.value:
        raise HTTPException(status_code=409, detail="Locked cast cannot be modified")
    if not role.selected_candidate_id:
        raise HTTPException(status_code=409, detail="Select a candidate before approving its reference")
    candidate = db.get(CharacterCandidate, role.selected_candidate_id)
    if candidate is None or candidate.role_id != role.id:
        raise HTTPException(status_code=409, detail="Selected candidate is unavailable")
    role.reference_image_url = candidate.image_url
    role.reference_approved = True
    db.commit()
    return serialize_casting(db, session)


@app.post(f"{settings.api_prefix}/casting/{{session_id}}/approve")
def approve_cast(session_id: str, db: Session = Depends(get_db)):
    session = db.get(CastingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Casting session not found")
    if session.status == CastingStatus.CAST_LOCKED.value:
        return serialize_casting(db, session)
    roles = get_casting_roles(db, session.id)
    if not roles or any(not role.selected_candidate_id or not role.reference_image_url
                        or not role.reference_approved for role in roles):
        raise HTTPException(status_code=409,
            detail="Every role needs a selected candidate and an approved reference")
    story = db.get(Story, session.story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    bible = dict(story.story_bible or {})
    characters = [item for item in bible.get("characters", [])
                  if item.get("casting_role_key") not in {role.role_key for role in roles}]
    for role in roles:
        definition = dict(role.role_definition)
        characters.append({
            "casting_role_key": role.role_key,
            "name": role.display_name,
            "narrative_function": definition.get("narrative_function"),
            "age_range": definition.get("age_range"),
            "personality": definition.get("personality"),
            "physical_description": definition.get("physical_description"),
            "wardrobe": definition.get("wardrobe"),
            "visual_style": definition.get("visual_style"),
            "reference_image_url": role.reference_image_url,
        })
    bible["characters"] = characters
    bible["canon_version"] = int(bible.get("canon_version", 1)) + 1
    story.story_bible = bible
    session.status = CastingStatus.CAST_LOCKED.value
    db.commit()
    return serialize_casting(db, session)
