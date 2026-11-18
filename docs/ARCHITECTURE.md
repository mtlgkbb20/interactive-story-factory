# Architecture

## Bounded contexts
- **Story Engine:** canonical story bible, characters, relationships, locations, world rules, timeline, episode summaries, unresolved threads, and candidate community ideas. Suggestions do not become canon automatically.
- **Community Engine:** separates explicit option votes from free-form feedback. The deterministic classifier is a conservative baseline; an LLM may enrich categories but must not silently turn prose into votes.
- **Production Engine:** turns an episode brief into scenes, narration, video clips, subtitles, and a vertical render. Provider adapters isolate model-specific APIs.
- **Workflow Engine:** explicit episode lifecycle with a mandatory human approval gate before publication.

## Vote integrity
Comment likes are not votes. Duplicate platform comment IDs are rejected. When author IDs exist, the tally accepts the first valid vote per author. When author identity is unavailable, the API reports that one-person-one-vote cannot be guaranteed.

## Provider strategy
Use canonical scene briefs and provider-specific prompt adapters. Persist model/version, prompt version, reference assets, cost, latency, and QC results. Verify model names, supported durations, aspect ratios, pricing, terms, and API availability before activation. ElevenLabs is the required TTS provider; ambient/foley/ASMR is a separate sound path.

## Social platform strategy
Begin with manual comment import. Official TikTok/Instagram access depends on account eligibility, scopes, app review, and publishing permissions. Do not rely on scraping or assume research APIs are available to ordinary creators.

## Runware provider integration
Runware is the shared gateway for text and video. Model selection is configured independently per
modality; auto delegates selection to the Runware router. Video tasks are asynchronous and polled
through getResponse. ElevenLabs remains the dedicated narration provider.
