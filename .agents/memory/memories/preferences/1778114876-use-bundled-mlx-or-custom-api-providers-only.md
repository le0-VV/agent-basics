---
record_kind: memory
ov_category: preferences
title: Use bundled MLX or custom API providers only
status: active
created: 1778114876
updated: 1778114876
tags: [runtime, openviking, mlx, custom-api]
summary: agent-basics now supports only the bundled MLX runtime or user-supplied custom OpenAI-compatible API providers; LM Studio and Ollama command families are not part of the public interface.
source_paths: []
requires_human_review: false
---

# Use bundled MLX or custom API providers only

Project: agent-basics

## Summary

agent-basics now supports only the bundled MLX runtime or user-supplied custom OpenAI-compatible API providers; LM Studio and Ollama command families are not part of the public interface.

## Content

Supersedes older LM Studio and Ollama runtime preferences. agent-basics should not expose, document, or route setup through provider-specific LM Studio or Ollama command families. The bundled local path is the agent-basics MLX server; any external runtime should be configured through OpenViking as a custom OpenAI-compatible API with explicit base URL, chat model, embedding model, and API key when needed.
