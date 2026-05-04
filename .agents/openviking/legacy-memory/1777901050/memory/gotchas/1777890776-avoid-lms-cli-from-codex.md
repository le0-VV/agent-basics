---
id: gotcha-1777890776-avoid-lms-cli-from-codex
type: gotcha
title: Avoid lms CLI from Codex
status: active
created: 1777890776
updated: 1777890776
tags: [lm-studio, macos, codex, crash]
summary: Calling the `lms` CLI from Codex can launch the LM Studio Electron app and crash during AppKit registration.
---

# Avoid lms CLI from Codex

## Problem

On macOS, calling `lms` from Codex caused LM Studio 0.4.12 to launch under the Codex process coalition and abort during AppKit application registration.

## Cause

The `lms` CLI can wake or launch the full LM Studio Electron application. That path is unsafe from the current sandboxed agent host.

## Workaround

Do not use `lms` from Codex. The user should start LM Studio and its local server manually. agent-basics should inspect and manage LM Studio through REST and OpenAI-compatible HTTP endpoints only.

## Related

- `scripts/agent_basics_ov.py`
- `README.md`
