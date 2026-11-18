# MVP Roadmap

## Foundation
- [x] FastAPI application and configuration
- [x] PostgreSQL-ready SQLAlchemy persistence
- [x] Persistent story bible data structure
- [x] Episode state machine with approval gate
- [x] Deterministic comment classification and vote tally
- [x] ElevenLabs TTS adapter boundary
- [x] Initial unit tests and CI
- [ ] Alembic migrations, authentication, admin review UI

## Story generation
- [ ] LLM provider and structured-output validation
- [ ] Episode outline/script generation
- [ ] Character sheets and reference image registry
- [ ] Continuity retrieval and contradiction checks
- [ ] Prompt versioning and evaluation fixtures

## Media production
- [ ] Image provider adapters
- [ ] At least two video model adapters
- [ ] Provider-specific prompt adapters and benchmark runner
- [ ] ElevenLabs voice profiles and pronunciation dictionary
- [ ] FFmpeg assembly, captions, sound mix, thumbnail
- [ ] Visual/audio QC and retry policy

## Community and distribution
- [ ] Manual CSV/JSON comment import
- [ ] LLM classification, confidence thresholds, moderation queue
- [ ] Story bible candidate review and acceptance
- [ ] Voting close scheduler and idempotent tally
- [ ] TikTok and Instagram official API capability spikes
- [ ] Publishing and analytics after permissions review

## Release gates
No public auto-publishing before human approval is reliable. No one-person-one-vote claim without stable author identity. No provider enabled before access, terms, pricing, and output rights are verified.
