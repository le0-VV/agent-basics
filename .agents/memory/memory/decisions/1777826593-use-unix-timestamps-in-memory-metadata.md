---
id: decision-1777826593-use-unix-timestamps-in-memory-metadata
type: decision
title: Use Unix timestamps in memory metadata
status: accepted
created: 1777826593
updated: 1777826593
tags: [memory, timestamps, schema]
summary: agent-basics memory metadata should use Unix timestamp seconds instead of ISO date strings.
---

# Use Unix timestamps in memory metadata

## Decision

agent-basics memory metadata should use Unix timestamp seconds instead of ISO date strings.

## Rationale

Unix timestamp seconds avoid ambiguous date-only values and give generated entries, lock metadata, manifests, and memory records one machine-friendly timestamp format.

## Consequences

Memory templates, schema validation, generated record IDs, generated filenames, event metadata, setup templates, config timestamps, and existing memory entries use Unix timestamp seconds. Event entries use event_timestamp instead of event_date.

## Related

- None.
