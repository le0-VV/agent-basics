---
id: event-1777766400-gemma-4-categorization-test
type: event
title: Gemma 4 categorization test
status: recorded
created: 1777766400
updated: 1777766400
tags: [memory, rag, lm-studio, gemma-4, categorization]
summary: Gemma 4 through LM Studio classified agent-basics memory categories accurately when constrained by JSON schema, but free-form JSON output was slow and wrapped in markdown fences.
event_timestamp: 1777766400
---

# Gemma 4 categorization test

## Event

Tested google/gemma-4-e4b through the local LM Studio API for routing incoming notes into decision, fact, preference, source, procedure, gotcha, and event. A 14-note free-form batch took 228.11 seconds and classified every note correctly, but returned markdown-fenced JSON despite strict JSON-only instructions, so raw parsing failed. A 5-note ambiguous set using LM Studio json_schema response_format returned valid JSON in 24.69 seconds with 5/5 correct. A single-note json_schema request returned valid JSON in 5.73 seconds with the expected gotcha category. Use schema-constrained output for any automated categorization path; avoid relying on free-form JSON instructions alone.

## Related

- None.
