---
id: fact-20260503-lm-studio-rest-api-manages-model-load-state
type: fact
title: LM Studio REST API manages model load state
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [lm-studio, models, setup, api]
summary: LM Studio's native /api/v1 models endpoints can list, load, configure, and unload local models; agent-basics can use them to manage local embedding and LLM runtime setup.
---

# LM Studio REST API manages model load state

## Fact

On 2026-05-03, the local LM Studio server at http://127.0.0.1:1234 exposed /api/v1/models with loaded instance config for text-embedding-embeddinggemma-300m-qat and google/gemma-4-e4b. A POST to /api/v1/models/load loaded text-embedding-nomic-embed-text-v1.5 with context_length 2048 and echo_load_config true, returning status loaded and the applied load_config. A POST to /api/v1/models/unload with instance_id text-embedding-nomic-embed-text-v1.5 unloaded that test model. This confirms agent-basics can programmatically manage model load/unload and load-time config without relying on the LM Studio UI.

## Related

- None.
