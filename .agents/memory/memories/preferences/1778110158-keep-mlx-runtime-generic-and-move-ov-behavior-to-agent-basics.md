---
record_kind: memory
ov_category: preferences
title: Keep MLX runtime generic and move OV behavior to agent-basics
status: active
created: 1778110158
updated: 1778110158
tags: []
summary: OpenViking-specific behavior belongs in agent-basics commands and checks, not inside the local LLM server.
source_paths: []
requires_human_review: false
---

# Keep MLX runtime generic and move OV behavior to agent-basics

Project: agent-basics

## Summary

OpenViking-specific behavior belongs in agent-basics commands and checks, not inside the local LLM server.

## Content

The user clarified that a lot of OpenViking-specific work is just agent-basics needing to make OpenViking do things. The local LLM server should stay generic: expose OpenAI-compatible chat, embeddings, model listing, health/readiness, and optional structured-output enforcement. agent-basics should own OpenViking setup, config writing, health checks, record/search/import flows, and macOS service/bootstrap behavior.
