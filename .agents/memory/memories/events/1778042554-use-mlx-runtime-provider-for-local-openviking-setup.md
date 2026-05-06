---
record_kind: memory
ov_category: events
title: Use MLX runtime provider for local OpenViking setup
status: active
created: 1778042554
updated: 1778042554
tags: [runtime, mlx, openviking]
summary: 
source_paths: []
requires_human_review: false
---

# Use MLX runtime provider for local OpenViking setup

Project: agent-basics

## Content

agent-basics should add a lightweight MLX local runtime provider using mlx-community/gemma-4-e2b-it-4bit for chat/VLM and mlx-community/embeddinggemma-300m-4bit for embeddings, exposed through an agent-basics-managed OpenAI-compatible server for OpenViking. Ollama remains a fallback because its resident memory behavior was too heavy on this host.
