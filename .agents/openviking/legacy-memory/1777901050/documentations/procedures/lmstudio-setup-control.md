---
id: procedure-1777895373-lmstudio-setup-control
type: procedure
title: Manage LM Studio setup for agent-basics
status: active
created: 1777895373
updated: 1777895373
tags: [lm-studio, openviking, gemma-4, embeddings, setup]
summary: Use agent-basics to verify LM Studio, write backed-up model defaults, load Gemma 4 E2B, and run the OV routing test without using the lms CLI.
---

# Manage LM Studio setup for agent-basics

## When To Use

Use this procedure when setting up or repairing the LM Studio runtime for agent-basics OpenViking work on macOS.

## Steps

1. Make sure the user has started LM Studio and its local server.
2. Run `agent-basics lmstudio status` and confirm `google/gemma-4-e2b` and `text-embedding-embeddinggemma-300m-qat` are present.
3. Run `agent-basics lmstudio configure` to dry-run persisted default changes.
4. Run `agent-basics lmstudio configure --write` to write backed-up defaults under `~/.lmstudio/.internal/user-concrete-model-default-config/`.
5. Run `agent-basics lmstudio load` to load Gemma 4 E2B through REST. Do not use the `lms` CLI from Codex.
6. Run `agent-basics lmstudio configure` again and confirm no mismatches remain.
7. Run `agent-basics lmstudio route-test` to verify the OV-native routing prompt and schema.

## Verification

`agent-basics lmstudio status` should report only `google/gemma-4-e2b` as the loaded Gemma LLM, with context length `131072`, eval batch size `512`, flash attention enabled, offload KV cache to GPU enabled, and parallel `1`. `agent-basics lmstudio configure` should report no mismatches for the E2B and EmbeddingGemma default config targets.

## Related

- `scripts/agent_basics_ov.py`
- `README.md`
- `.agents/memory/memory/gotchas/1777890776-avoid-lms-cli-from-codex.md`
- `.agents/memory/memory/gotchas/1777892749-lm-studio-rest-load-config-limits.md`
