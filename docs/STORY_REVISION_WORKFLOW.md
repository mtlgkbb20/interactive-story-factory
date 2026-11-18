# Story revision workflow

Story revision is a proposal-and-approval workflow. It never overwrites prior versions.

## User flow

1. Submit free-form feedback and a scope (whole_story, premise, characters, ending, or tone).
2. The text model proposes a new title and premise plus a summary of changes.
3. The response identifies affected Story Bible sections and any proposed non-character updates.
4. Review the proposal. Approve it or reject it; rejected and prior versions remain in history.
5. A new revision cannot be requested while another revision is awaiting approval.

## API

- GET /api/v1/stories/{story_id}/revisions: list versions newest first.
- POST /api/v1/stories/{story_id}/revisions: create a proposal.
  Body: {"feedback":"Make the premise less predictable","scope":"whole_story"}
- POST /api/v1/stories/{story_id}/revisions/{revision_id}/approve: approve and apply the proposal.
  If non-character Story Bible updates exist, explicitly send {"approve_story_bible_updates":true}.
- POST /api/v1/stories/{story_id}/revisions/{revision_id}/reject: reject the proposal.

## Invariants

- Version 1 is captured when a story is created; legacy stories get a baseline snapshot on first history access/revision.
- A proposed revision is not live until approved.
- Every revision stores its feedback, generated title/premise, Story Bible snapshot, impact list and proposed updates.
- Character records and approved visual reference URLs are protected from this workflow.
- Only allowlisted non-character Story Bible sections can be updated, and only with explicit approval.
- Existing episodes and media assets are not regenerated or modified.
- The current casting session and its lock state are not changed by story revision.

This first backend release revises the story title/premise. Fine-grained episode/script rewriting is separate work and does not happen implicitly.
