---
id: event-20260503-dogfood-sample-subagent-run
type: event
title: Dogfood sample subagent run
status: recorded
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, dogfood, subagents, setup]
summary: Two sample repos were set up with agent-basics and exercised by subagents; setup worked, one worker completed independently, and Python workers exposed completion/rebuild friction.
event_date: 2026-05-03
---

# Dogfood sample subagent run

## Event

Created `sample-node` and `sample-python` repositories under `/private/tmp/agent-basics-dogfood.FitUca`, ran `agent-basics setup` against both with the LM Studio embedding API, and delegated feature work to worker subagents. The Node worker completed implementation, tests, no-rebuild memory recording, validation, and commit. The first Python worker stalled without changes; the replacement worker implemented code and memory but stalled before tests/commit, requiring manual completion.

Dogfood findings: setup health was good, `memory_record --no-rebuild` was smooth, post-commit hook auto-rebuild defeated approval-light behavior, copied project instructions add about 1.3k words of always-read overhead, and sample commits can still miss committer-name policy depending on how subagents invoke git.

## Notes

Immediate fix: `post-commit`, `post-merge`, and `post-checkout` hooks now warn on stale indexes by default; `AGENT_BASICS_HOOK_AUTO_REBUILD=1` opts back into automatic hook rebuilds.

## Related

- memory/decisions/20260503-defer-memory-rebuilds-for-routine-mcp-records.md
