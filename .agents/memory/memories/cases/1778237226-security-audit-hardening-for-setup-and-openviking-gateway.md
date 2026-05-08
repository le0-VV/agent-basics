---
record_kind: memory
ov_category: cases
title: Security audit hardening for setup and OpenViking gateway
status: active
created: 1778237226
updated: 1778237226
tags: [security, audit, setup, mcp, prompt-injection]
summary: 
source_paths: []
requires_human_review: false
---

# Security audit hardening for setup and OpenViking gateway

Project: agent-basics

## Content

A security audit with subagents tested setup/install symlink clobbering, hostile PATH/project names, markdown merge conflicts, MCP cwd/repo confusion, Viking URI namespace escapes, external file ingestion, secret leakage in status/config output, stale hook lock denial of service, spoofed .git worktree metadata, and prompt injection in retrieved OpenViking context. Fixes added repo-local path assertions in setup-macos.sh, sanitized PATH ordering, bounded OpenViking record slugs, repo-scoped URI validation, external path rejection for resources/skills, sensitive output redaction, stale lock recovery, git hook installer validation, and generated prompt-injection trust-boundary guidance. Verification passed with ./agent-basics verify, including 145 Python tests, cargo test, setup syntax, Homebrew formula syntax, OpenViking offline status, and licensing notices.
