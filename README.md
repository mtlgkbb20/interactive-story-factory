# Interactive Story Factory

An AI-assisted production pipeline for realistic, audience-directed short-form episodic stories.

The project turns a story bible, episode brief, scene plan, and community feedback into reviewable vertical-video episodes. Audience decisions and free-form comments influence future episodes while continuity and human approval remain explicit.

## Status

**Foundation / MVP scaffold.** Provider integrations are expressed as interfaces; credentials and provider-specific API implementations must be configured before production use.

## Core loop

1. Create a story and its persistent story bible.
2. Generate an episode outline, script, scenes, and audience choices.
3. Produce narration and scene videos through replaceable providers.
4. Assemble a vertical video and run quality checks.
5. Require human approval before publishing.
6. Collect comments, classify explicit votes separately from free-form feedback, and close voting.
7. Update the story bible and plan the next episode.

## Architecture

- **Story engine:** canon, characters, relationships, locations, unresolved threads, episode summaries, continuity checks.
- **Production engine:** script/scene contracts, provider abstractions, ElevenLabs TTS adapter, render orchestration.
- **Community engine:** deterministic vote parsing, duplicate policy hooks, comment classification, suggestion backlog.
- **Workflow engine:** explicit episode lifecycle transitions and human approval gates.
- **API:** FastAPI endpoints for stories, episodes, comments, votes, and health.
- **Persistence:** SQLAlchemy models with PostgreSQL-ready configuration; SQLite can be used for local tests.

## Quick start

Requires Python 3.11+.

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn apps.api.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

Run tests:

```bash
pytest
```

## Important platform constraints

TikTok and Instagram integrations are provider boundaries, not assumptions of unrestricted access. Comment retrieval and publishing depend on platform app review, account permissions, scopes, and API availability. The MVP supports manual comment ingestion; do not scrape platform pages as the primary integration.

## Configuration

See [.env.example](.env.example). Never commit API keys, access tokens, generated media, or local database files.

## Development principles

- One comment can contribute either an explicit vote or free-form feedback; it must not silently count as both.
- Vote percentages are based on valid, deduplicated votes, not comment likes.
- Identity-based one-person-one-vote is only enforceable when the platform supplies a stable author identifier.
- Community suggestions are candidates, not automatic canon. Story continuity and safety checks must pass.
- All generated episodes remain pending human approval until explicitly approved.
- Model names, API capabilities, pricing, and availability must be verified against current provider documentation before enabling an adapter.

## Roadmap

See [docs/MVP_ROADMAP.md](docs/MVP_ROADMAP.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).


## Story casting\n\nThe story-specific casting flow is documented in [docs/CASTING_WORKFLOW.md](docs/CASTING_WORKFLOW.md). It creates role definitions with the text model, generates four portrait candidates per role with Runware image inference, and requires explicit selection and reference approval before the cast can be locked. Set `RUNWARE_IMAGE_MODEL` in `.env`; `auto` uses Runware model routing. Reference-image conditioning is model-dependent.\n\n## Runware setup

Set RUNWARE_API_KEY in .env. Text and video models are configured separately and default to auto.
POST /api/v1/stories/{story_id}/episodes/generate creates a structured episode from the Story Bible.
POST /api/v1/media/video submits a video task; GET /api/v1/media/tasks/{task_uuid} polls it.
Runware returns the output URL and cost. Multi-clip rendering and media persistence remain separate
production steps; ElevenLabs narration remains configured independently.
