---
id: event-1777892177-gemma-4-e2b-ov-routing-test
type: event
title: Gemma 4 E2B OV routing test
status: recorded
created: 1777892177
updated: 1777893388
tags: [gemma-4, e2b, openviking, routing, lm-studio]
summary: Gemma 4 E2B reached 59/59 on the OV-native routing test after deterministic pre-ingest supplied action, record kind, and category hints.
event_timestamp: 1777892177
---

# Gemma 4 E2B OV routing test

## Event

After LM Studio HTTP was restarted, `agent-basics lmstudio route-test` was run against `google/gemma-4-e2b`. Prompt-only routing scored 39/59, then 44/59 after stronger rules. The final version added deterministic pre-ingest hints for action, record kind, and OV category and scored 59/59. A later rerun after fixing the LM Studio REST load payload also scored 59/59.

## Impact

Gemma 4 E2B is good enough for agent-basics OV routing when deterministic pre-ingest owns obvious routing constraints and the local model shapes the resulting OV records. The local model alone should not be trusted as the only categorizer.

## Related

- `scripts/agent_basics_ov.py`
- `.agents/memory/memory/preferences/1777890776-use-gemma-4-e2b-by-default.md`
- `.agents/memory/memory/gotchas/1777890776-avoid-lms-cli-from-codex.md`
