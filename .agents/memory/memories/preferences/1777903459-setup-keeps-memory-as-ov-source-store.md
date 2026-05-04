---
id: ov-memory-1777903459-setup-keeps-memory-as-ov-source-store
record_kind: memory
ov_category: preferences
title: Setup keeps .agents/memory as the OV source store
status: active
created: 1777903459
updated: 1777903459
tags: [agent-basics, setup, openviking, migration]
summary: The user wants setup to preserve `.agents/memory/` as the repo-specific OpenViking source store and snapshot legacy material for adaptation.
source_paths: []
requires_human_review: false
---

# Setup keeps .agents/memory as the OV source store

The user wants `.agents/memory/` to remain the future repo-specific OpenViking source store. Setup should not delete that directory, should not reinstall the legacy mini-RAG layout by default, and should copy existing compatibility memory material to a safe legacy snapshot for later adaptation into OV-compliant records.

