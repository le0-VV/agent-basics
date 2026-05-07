---
record_kind: memory
ov_category: events
title: Packaged OpenViking server executable
status: active
created: 1778118781
updated: 1778118781
tags: [openviking, packaging, launchagent]
summary: 
source_paths: []
requires_human_review: false
---

# Packaged OpenViking server executable

Project: agent-basics

## Content

Agent-basics now packages the global OpenViking HTTP server into ~/.openviking/openviking with PyInstaller so the LaunchAgent process is named openviking instead of python3.12. The package recipe explicitly adds openviking/lib/ragfs_python.abi3.so and uses package_revision=2 so older broken packages are rebuilt. Verified on 2026-05-07 with agent-basics ov doctor --online, direct /health, and ps showing /Users/leonardw/.openviking/openviking.
