# Legacy Memory Snapshots

This directory preserves pre-OpenViking agent-basics memory source trees for migration and audit.

The target repo-owned source store is `.agents/memory/`. Legacy snapshots here are not the canonical active memory layout. Agents may inspect them while adapting records into OpenViking categories, but should not add new durable memory here unless explicitly preserving migration input.

## Snapshots

- `1777901050/`: compatibility `.agents/memory/` markdown source and mini-RAG helper files copied before redirecting `.agents/memory/` toward the OpenViking source-store layout.
