# Memory Index

This index is maintained by agents and setup tooling. Update it whenever entries are added, moved, or removed.

## OpenViking Source Store

- [Schema](SCHEMA.md)
- [Adaptation guide](ADAPTATION.md)
- `memories/`: OV-native memory source records grouped by OpenViking category.
- `resources/`: documentation and references to ingest as OpenViking resources.
- `skills/`: reusable workflows to register as OpenViking skills.
- `imports/`: copied source material awaiting adaptation.
- [Keep .agents/memory as the OpenViking source store](memories/preferences/1777901050-keep-memory-as-ov-source-store.md)
- [Setup keeps .agents/memory as the OV source store](memories/preferences/1777903459-setup-keeps-memory-as-ov-source-store.md)
- [Installation-wide agent-basics language](memories/preferences/1777944754-installation-wide-agent-basics-language.md)
- [Homebrew install bootstraps OpenViking](memories/preferences/1777946105-homebrew-install-bootstraps-openviking.md)
- [Legacy compatibility memory snapshot created](memories/events/1777901050-legacy-memory-snapshot-created.md)
- [OpenViking rejects zero VLM timeout](memories/cases/1777909438-openviking-rejects-zero-vlm-timeout.md)
- [Persistent LM Studio routing defaults can conflict with OpenViking](memories/cases/1777910744-lmstudio-routing-defaults-conflict-with-openviking.md)

## Legacy Compatibility Snapshot

- `.agents/openviking/legacy-memory/1777901050/` preserves the compatibility markdown source tree that existed before `.agents/memory/` was redirected toward the OpenViking source-store layout.
- `compat/memory-rag/` contains the fallback mini-RAG implementation source used only for explicit compatibility installs.
