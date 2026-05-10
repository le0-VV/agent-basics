---
record_kind: memory
ov_category: cases
title: LaunchAgent cleanup for AB MLX and OpenViking
status: active
created: 1778381562
updated: 1778381562
tags: []
summary: 
source_paths: []
requires_human_review: false
---

# LaunchAgent cleanup for AB MLX and OpenViking

Project: agent-basics

## Content

Optimizer apps such as Sensei scan ~/Library/LaunchAgents and may treat timestamped .plist.bak files as separate launch-agent configs. agent-basics service installers should archive service plist backups under the service home backups/launchagents directory instead of leaving them beside active plists. Global OpenViking service install should also disable and remove deprecated repo-local OpenViking LaunchAgents for the current repo.
