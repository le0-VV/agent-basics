---
record_kind: memory
ov_category: events
title: Patched MLX server response_format and idle timer after live OpenViking test
status: active
created: 1778048030
updated: 1778048030
tags: [mlx, openviking, runtime, testing]
summary: The custom agent-basics MLX server was live-tested with EmbeddingGemma and Gemma 4 E2B. Direct embeddings and chat worked; response_format initially returned fenced JSON and was patched to inject JSON/schema instructions and normalize fenced/prose JSON. OpenViking search through MLX initially repeated cold 150s embedding loads because last_used was touched at request start; the server now refreshes idle time after embedding/chat inference, and OV search had one cold 153s call followed by sub-second scoped searches.
source_paths: []
requires_human_review: false
---

# Patched MLX server response_format and idle timer after live OpenViking test

Project: agent-basics

## Summary

The custom agent-basics MLX server was live-tested with EmbeddingGemma and Gemma 4 E2B. Direct embeddings and chat worked; response_format initially returned fenced JSON and was patched to inject JSON/schema instructions and normalize fenced/prose JSON. OpenViking search through MLX initially repeated cold 150s embedding loads because last_used was touched at request start; the server now refreshes idle time after embedding/chat inference, and OV search had one cold 153s call followed by sub-second scoped searches.

## Content

On 1778047xxx, agent-basics MLX runtime testing reached a working state. The downloaded MLX models are mlx-community/gemma-4-e2b-it-4bit and mlx-community/embeddinggemma-300m-4bit. Direct /health and /v1/models worked without loading models. Direct /v1/embeddings worked after a cold load. Direct /v1/chat/completions worked, but Gemma initially returned markdown-fenced JSON; scripts/agent_basics_mlx_server.py now handles response_format by adding request-time JSON/schema instructions and extracting valid JSON from fenced or prose output. During OpenViking search testing, each scope initially caused another cold embedding load because RuntimeState.last_used was updated before the long embedding call and the test server had a 120 second idle window. The server now calls state.touch() after embedding and chat inference, so the model stays warm after slow requests. Retest through agent-basics ov search showed the first MLX embedding call took about 153 seconds and all later scoped searches completed in roughly 0.06 to 0.16 seconds. The managed MLX LaunchAgent com.agent-basics.mlx-runtime is installed with unload_idle_seconds 600, and OpenViking config points to http://127.0.0.1:18080/v1 for chat/VLM and embeddings.
