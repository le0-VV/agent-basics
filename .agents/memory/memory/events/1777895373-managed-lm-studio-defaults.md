---
id: event-1777895373-managed-lm-studio-defaults
type: event
title: Managed LM Studio defaults for E2B
status: recorded
created: 1777895373
updated: 1777895373
tags: [lm-studio, gemma-4, e2b, openviking, routing]
summary: agent-basics wrote backed-up LM Studio defaults for Gemma 4 E2B and EmbeddingGemma, loaded E2B, and passed the OV routing test.
event_timestamp: 1777895373
---

# Managed LM Studio defaults for E2B

## Event

`agent-basics lmstudio configure --write` updated the LM Studio default config files for `google/gemma-4-e2b`, its concrete GGUF config, `text-embedding-embeddinggemma-300m-qat`, and its concrete GGUF config. Existing files were backed up beside the originals with `.bak.1777895359` suffixes.

`agent-basics lmstudio load` then loaded `google/gemma-4-e2b` through REST in 5.48 seconds. LM Studio reported context length `131072`, eval batch size `512`, flash attention enabled, offload KV cache to GPU enabled, and parallel `1`. `agent-basics lmstudio route-test` scored 59/59.

## Impact

agent-basics can now own the local LM Studio setup needed for OpenViking routing without using the `lms` CLI from Codex. Persisted defaults cover CPU threads, concurrency, context length, GPU offload ratio, KV cache quantization, routing system prompt, temperature, and structured-output schema where LM Studio stores those fields.

## Related

- `scripts/agent_basics_ov.py`
- `.agents/memory/documentations/procedures/lmstudio-setup-control.md`
- `.agents/memory/memory/events/1777892177-gemma-4-e2b-ov-routing-test.md`
