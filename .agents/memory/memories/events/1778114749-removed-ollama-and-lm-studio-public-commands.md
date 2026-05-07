---
record_kind: memory
ov_category: events
title: Removed Ollama and LM Studio public commands
status: active
created: 1778114749
updated: 1778114749
tags: [runtime, openviking, mlx, custom-api]
summary: agent-basics now exposes bundled MLX or custom OpenAI-compatible API provider paths only
source_paths: []
requires_human_review: false
---

# Removed Ollama and LM Studio public commands

Project: agent-basics

## Summary

agent-basics now exposes bundled MLX or custom OpenAI-compatible API provider paths only

## Content

agent-basics removed the public ollama and lmstudio top-level command dispatchers and no longer advertises or parses provider-specific Ollama or LM Studio command families. OpenViking provider choices are now mlx or custom; runtime bootstrap choices are auto, mlx, or none. provider=custom requires a base URL plus chat and embedding model ids, and runtime=auto skips bundled runtime bootstrap for custom providers. Documentation, setup templates, roadmap, licensing notices, and tests were updated to describe MLX as the bundled runtime and custom OpenAI-compatible APIs as the non-MLX path.
