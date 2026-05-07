---
record_kind: memory
ov_category: events
title: Packaged MLX server as standalone executable
status: active
created: 1778113817
updated: 1778113817
tags: [mlx, packaging, launchd]
summary: agent-basics MLX server now packages to a one-file executable
source_paths: []
requires_human_review: false
---

# Packaged MLX server as standalone executable

Project: agent-basics

## Summary

agent-basics MLX server now packages to a one-file executable

## Content

agent-basics now adds agent-basics mlx package, which uses PyInstaller in the user-level MLX venv to build ~/.agent-basics/mlx/agent-basics-mlx from scripts/agent_basics_mlx_server.py. agent-basics mlx bootstrap packages the server by default before installing the macOS LaunchAgent, while --package-server never keeps the old script-copy write-server fallback. The LaunchAgent now points at the standalone executable, so process listings show agent-basics-mlx instead of python3.12. launchctl bootstrap calls retry transient return code 5 failures. The generated PyInstaller bundle is user-local and must not be committed or redistributed without dependency/license audit. In Codex sandbox, running the PyInstaller one-file executable can fail on semaphore initialization, but it works outside the sandbox and as the LaunchAgent process.
