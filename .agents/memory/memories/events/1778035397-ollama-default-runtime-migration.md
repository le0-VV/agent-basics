---
record_kind: memory
ov_category: events
title: Ollama default runtime migration
status: active
created: 1778035397
updated: 1778035397
tags: [runtime, ollama, openviking]
summary: 
source_paths: []
requires_human_review: false
---

# Ollama default runtime migration

Project: agent-basics

## Content

On 1778035397, agent-basics moved its active local runtime configuration from LM Studio to Ollama. User-level OpenViking config now points chat/VLM to gemma4:e2b and embeddings to embeddinggemma:latest at http://127.0.0.1:11434/v1. LM Studio remains a legacy optional provider only.
