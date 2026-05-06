---
record_kind: memory
ov_category: events
title: MLX OpenViking live round trip demo
status: active
created: 1778110649
updated: 1778110649
tags: []
summary: Live demo verified the agent-basics MLX server is reachable through OpenViking and can support record/search/read flow.
source_paths: []
requires_human_review: false
---

# MLX OpenViking live round trip demo

Project: agent-basics

## Summary

Live demo verified the agent-basics MLX server is reachable through OpenViking and can support record/search/read flow.

## Content

On 1778110636, agent-basics mlx status reported the local MLX server healthy at http://127.0.0.1:18080 with chat model mlx-community/gemma-4-e2b-it-4bit and embedding model mlx-community/embeddinggemma-300m-4bit loaded. The demo records this event through agent-basics ov to prove OpenViking can write memory using the configured local MLX-backed provider path.
