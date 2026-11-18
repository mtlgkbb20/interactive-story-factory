# Provider Integration

## Canonical scene brief
Each scene defines subject/action, location/time, character reference IDs, camera framing/movement, lighting, dialogue, sound design, target duration, 9:16 aspect ratio, negative constraints, and continuity constraints.

## Adapter contract
Implement the VideoProvider scene-generation contract and return GeneratedAsset. Persist the canonical brief and exact model-specific prompt. Classify retryable rate limits/timeouts separately from invalid requests and policy refusals.

## Benchmark protocol
Run identical briefs against at least three eligible models where access permits. Record model/version, prompt template version, reference asset hashes, output URI/duration, latency/cost, prompt adherence, motion naturalness, realism, character consistency, and reviewer notes.

Initial score weights: realism 25%, motion 20%, prompt adherence 20%, retention potential 15%, audio 10%, character consistency 10%. Calibrate using actual evaluations.

## ElevenLabs
Use ElevenLabs for spoken narration and character dialogue. Keep voice IDs in configuration. Ambient, Foley, and ASMR sound use a separate sound-design path.
