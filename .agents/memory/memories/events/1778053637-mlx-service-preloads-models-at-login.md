---
record_kind: memory
ov_category: events
title: MLX service preloads models at login
status: active
created: 1778053637
updated: 1778053637
tags: [mlx, openviking, launchagent]
summary: agent-basics MLX LaunchAgent preloads chat and embedding models at macOS login and validates the OpenViking router schema during startup.
source_paths: []
requires_human_review: false
---

# MLX service preloads models at login

Project: agent-basics

## Summary

agent-basics MLX LaunchAgent preloads chat and embedding models at macOS login and validates the OpenViking router schema during startup.

## Content

On 1778053499, the updated agent-basics MLX LaunchAgent completed startup preload with chat_loaded=true, embedding_loaded=true, preload=complete, and structured_output.ok=true/items=1. The service uses --unload-idle-seconds 0, --preload-models all, and --startup-structured-output-check openviking-router. The measured startup preload took about 334 seconds on this host. Request-time response_format remains authoritative for OpenViking calls; startup warmup is a health check and model warm path.
