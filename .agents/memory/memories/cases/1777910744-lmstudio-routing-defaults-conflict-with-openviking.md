---
id: ov-memory-1777910744-lmstudio-routing-defaults-conflict-with-openviking
record_kind: memory
ov_category: cases
title: Persistent LM Studio routing defaults can conflict with OpenViking
status: active
created: 1777910744
updated: 1777910744
tags: [openviking, lmstudio, structured-output, config]
summary: Persisted LM Studio structured-output or system-prompt defaults can conflict with OpenViking's own request-time grammar; keep routing schema request-scoped.
source_paths: []
requires_human_review: false
---

# Persistent LM Studio routing defaults can conflict with OpenViking

## Problem

OpenViking memory extraction through LM Studio can fail with `Cannot combine structured output constraints with lazy grammar` when the loaded chat model has persisted structured-output defaults from earlier routing tests.

## Workaround

`agent-basics lmstudio configure --write` should clear stale persisted `llm.prediction.structured` and `llm.prediction.systemPrompt` defaults. Keep the OpenViking routing system prompt and JSON schema on explicit `agent-basics lmstudio route-test` requests instead of making them model-wide LM Studio defaults.
