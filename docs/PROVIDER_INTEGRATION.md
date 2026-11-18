# Provider Integration

## Runware
Runware is the unified inference gateway for text, image and video. Configure RUNWARE_API_KEY once.
Text and video models are independent settings (RUNWARE_TEXT_MODEL and RUNWARE_VIDEO_MODEL).
Both default to auto so Runware's model router selects a suitable model; pin an AIR identifier
when a reproducible model is required.

Text uses textInference and validates generated JSON before saving an episode. Video uses
videoInference with deliveryMethod=async. Keep its task UUID and poll getResponse until success
or error. Store model, prompt, task UUID, output URL and cost.

## ElevenLabs
ElevenLabs remains the dedicated narration provider. Voice IDs and model are configured in .env.
