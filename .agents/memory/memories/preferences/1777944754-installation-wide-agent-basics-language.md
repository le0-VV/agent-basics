---
record_kind: memory
ov_category: preferences
title: Installation-wide agent-basics language
status: active
created: 1777944754
updated: 1777944754
tags: [setup, language]
summary: agent-basics language is an installation-level preference, not repo-local config.
source_paths: []
requires_human_review: false
---

# Installation-wide agent-basics language

Project: agent-basics

## Summary

agent-basics language is an installation-level preference, not repo-local config.

## Content

Language selection for agent-basics must be shared by the installation. Setup should persist the preference in the agent-basics user config, normally ~/.agent-basics/config.toml, and repo .agents/config.toml must not own [agent_basics].language. Existing repo-scoped language keys should be removed during setup/upgrade.
