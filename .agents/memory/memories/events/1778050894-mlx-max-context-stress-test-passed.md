---
record_kind: memory
ov_category: events
title: MLX max-context stress test passed
status: completed
created: 1778050894
updated: 1778050894
tags: [mlx, stress-test, openviking]
summary: MLX server completed a near-max 130k-token chat prefill and returned HTTP 200; route thread fix verified, but host swapped heavily and service is single-flight during long chat calls.
source_paths: [/private/tmp/agent_basics_mlx_stress_result.md]
requires_human_review: false
---

# MLX max-context stress test passed

Project: agent-basics

## Summary

MLX server completed a near-max 130k-token chat prefill and returned HTTP 200; route thread fix verified, but host swapped heavily and service is single-flight during long chat calls.

## Content

# MLX max-context stress test result

agent-basics MLX runtime stress testing on 2026-05-06 completed a near-max context chat request against `mlx-community/gemma-4-e2b-it-4bit` through the OpenAI-compatible MLX server at `http://127.0.0.1:18080`.

Observed result:
- The server completed prefill for `130007/130008` tokens and logged `POST /v1/chat/completions` as HTTP 200.
- The model config advertises `text_config.max_position_embeddings = 131072`.
- The service remained healthy after the run with chat loaded and embedding unloaded.
- Focused MLX server tests passed: `python -m unittest tests.test_agent_basics_mlx_server`.
- Full project verification passed: `./agent-basics verify`.

Operational notes:
- A previous service-mode call failed with `There is no Stream(gpu, 0) in current thread`; converting the FastAPI embeddings and chat routes to `async def` fixed the route thread issue.
- At 130k context on this host, throughput degraded sharply after roughly 110k tokens and macOS VM stats showed heavy swapping. The server survives the request, but long chat calls effectively block the single MLX HTTP service until the call finishes.
- The temporary stress harness originally used an inefficient prompt builder. A linear prompt builder is preferable for future max-context tests.
