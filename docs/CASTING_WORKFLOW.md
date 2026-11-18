# Story-specific casting workflow

Casting is a required, story-scoped gate before script and scene production.

## Flow

1. Create a story and request a cast. The Casting Director returns 2-6 narrative roles.
2. Each role receives four distinct portrait candidates generated with the same visual direction.
3. The user selects one candidate for every role. Candidates remain immutable.
4. Selected portraits become reference images. The user explicitly approves the reference package.
5. The cast is locked. Episode generation can then include the approved cast bible and reference URLs.
6. A role can be reopened independently; existing candidates, approved references and scene assets are not overwritten.

## API

- `POST /api/v1/stories/{story_id}/casting`: generate a cast and persist role definitions.
- `GET /api/v1/casting/{session_id}`: read session, roles and candidate images.
- `POST /api/v1/casting/{session_id}/roles/{role_id}/candidates`: generate four candidates for one role.
- `POST /api/v1/casting/{session_id}/roles/{role_id}/select`: select one candidate.
- `POST /api/v1/casting/{session_id}/roles/{role_id}/reference`: promote selected candidate to the role's reference image.
- `POST /api/v1/casting/{session_id}/approve`: lock the cast after every role has a selected and approved reference.

## Provider notes

Image generation uses Runware `imageInference`. The configured `RUNWARE_IMAGE_MODEL` defaults to `auto`.
Reference conditioning is passed as `inputs.referenceImages`; support is model-specific. The selected model
must be checked against its Runware schema before enabling reference-conditioned regeneration or character
sheet generation. This initial implementation uses the selected candidate portrait as the approved reference;
multi-angle sheets and persistent media downloads are follow-up work. Runware output URLs are temporary
provider URLs, so production deployments should copy approved assets into durable object storage.

## State and invariants

- Casting sessions and roles belong to exactly one story.
- A role has four candidate records per generation attempt; old candidates are retained.
- A role cannot be selected from another role or another casting session.
- A cast cannot be locked until all roles have a selected candidate and an approved reference URL.
- Casting never overwrites Story Bible data or generated media.
- The episode-generation endpoint is not silently changed to bypass casting; enforcing the gate on episode
  generation is a separate integration step once the UI and image persistence lifecycle are ready.
