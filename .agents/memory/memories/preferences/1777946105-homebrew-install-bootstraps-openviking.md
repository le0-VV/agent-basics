---
record_kind: memory
ov_category: preferences
title: Homebrew install bootstraps OpenViking
status: active
created: 1777946105
updated: 1777946105
tags: [install, openviking]
summary: agent-basics Homebrew installs must bootstrap OpenViking automatically.
source_paths: []
requires_human_review: false
---

# Homebrew install bootstraps OpenViking

Project: agent-basics

## Summary

agent-basics Homebrew installs must bootstrap OpenViking automatically.

## Content

Installing agent-basics through Homebrew should automatically check for a user-level OpenViking installation and bootstrap it when missing. The bootstrap path should install OpenViking under ~/.openviking, write default ov.conf and ovcli.conf if missing, and attempt to install the macOS LaunchAgent. Manual install-system and write-default-config commands are lower-level repair commands.
