---
id: decision-1777890776-use-openviking-native-memory-categories
type: decision
title: Use OpenViking-native memory categories
status: accepted
created: 1777890776
updated: 1777890776
tags: [openviking, memory, migration, categories]
summary: agent-basics should migrate custom memory records into OpenViking's native categories instead of maintaining a parallel taxonomy.
---

# Use OpenViking-native memory categories

## Decision

agent-basics should completely use OpenViking's native memory categories for migrated memory: profile, preferences, entities, events, cases, patterns, tools, and skills.

## Rationale

The custom decision/fact/preference/source/procedure/gotcha/event taxonomy overlaps with OpenViking's own memory extractor. Keeping both would add prompt overhead and create category drift.

## Consequences

Legacy decisions become events unless they describe an ongoing preference. Legacy facts become entities. Legacy procedures become patterns or skills. Legacy gotchas become cases or reusable patterns. Source records stay out of memory and should become resources when useful.

## Related

- `.agents/memory/INDEX.md`
- `ROADMAP.md`
