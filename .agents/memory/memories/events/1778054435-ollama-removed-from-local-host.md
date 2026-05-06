---
record_kind: memory
ov_category: events
title: Ollama removed from local host
status: active
created: 1778054435
updated: 1778054435
tags: [ollama, mlx, openviking]
summary: Ollama app, CLI symlink, model store, and support files were removed; OpenViking remains configured for agent-basics MLX.
source_paths: []
requires_human_review: false
---

# Ollama removed from local host

Project: agent-basics

## Summary

Ollama app, CLI symlink, model store, and support files were removed; OpenViking remains configured for agent-basics MLX.

## Content

On 1778054367, Ollama models gemma4:e2b, embeddinggemma:latest, kimi-k2:1t-cloud, qwen3-coder:480b-cloud, gpt-oss:20b-cloud, and gpt-oss:120b-cloud were deleted with ollama rm. The com.ollama.ollama background job was booted out. /Applications/Ollama.app, /usr/local/bin/ollama, ~/.ollama, and main Ollama user support files were removed. Verification showed ollama not found, no com.ollama.ollama launchd service, no Homebrew cask/formula listing, and OpenViking still using the MLX provider at http://127.0.0.1:18080/v1.
