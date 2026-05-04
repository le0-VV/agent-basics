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
- [Legacy compatibility memory snapshot created](memories/events/1777901050-legacy-memory-snapshot-created.md)

## Legacy Compatibility Snapshot

- `.agents/openviking/legacy-memory/1777901050/` preserves the compatibility markdown source tree that existed before `.agents/memory/` was redirected toward the OpenViking source-store layout.

The sections below are the legacy mini-RAG index and remain temporarily useful while compatibility commands still exist.

## Decisions

- [Use repo-local structured memory with generated RAG support](memory/decisions/repo-local-memory-rag.md)
- [Keep root Agents.md as the agent entrypoint](memory/decisions/1777766400-keep-root-agents-md-as-the-agent-entrypoint.md)
- [Use Rust for the agent-basics binary](memory/decisions/1777766400-use-rust-for-the-agent-basics-binary.md)
- [Retire the agent mailbox](memory/decisions/1777766400-retire-the-agent-mailbox.md)
- [Polish memory recorder output](memory/decisions/1777766400-polish-memory-recorder-output.md)
- [Defer memory rebuilds for routine MCP records](memory/decisions/1777766400-defer-memory-rebuilds-for-routine-mcp-records.md)
- [Make agent-basics an OpenViking-backed repo harness](memory/decisions/1777852800-make-agent-basics-an-openviking-backed-repo-harness.md)
- [Use Unix timestamps in memory metadata](memory/decisions/1777826593-use-unix-timestamps-in-memory-metadata.md)
- [Use OpenViking-native memory categories](memory/decisions/1777890776-use-openviking-native-memory-categories.md)

## Facts

- [LM Studio REST API manages model load state](memory/facts/1777766400-lm-studio-rest-api-manages-model-load-state.md)

## Preferences

- [Keep markdown files ending with an empty trailing line](memory/preferences/agent-basics.md)
- [Use Gemma 4 E2B by default](memory/preferences/1777890776-use-gemma-4-e2b-by-default.md)

## Gotchas

- [Avoid lms CLI from Codex](memory/gotchas/1777890776-avoid-lms-cli-from-codex.md)
- [LM Studio REST load config limits](memory/gotchas/1777892749-lm-studio-rest-load-config-limits.md)

## Events

- [Dogfood sample subagent run](memory/events/1777766400-dogfood-sample-subagent-run.md)
- [Gemma 4 categorization test](memory/events/1777766400-gemma-4-categorization-test.md)
- [Gemma 4 E2B OV routing test](memory/events/1777892177-gemma-4-e2b-ov-routing-test.md)
- [Managed LM Studio defaults for E2B](memory/events/1777895373-managed-lm-studio-defaults.md)

## Documentation Sources

- [agent-basics documentation sources](documentations/sources/agent-basics.md)
- [Legacy OpenViking documentation index](documentations/sources/legacy-openviking-documentations.md)

## Procedures

- [Use the agent-basics OpenViking gateway](documentations/procedures/openviking-gateway.md)
- [Use the compatibility agent-basics memory MCP server](documentations/procedures/agent-memory-mcp.md)
- [Use the compatibility agent-basics memory CLI](documentations/procedures/agent-memory-cli.md)
- [Run the compatibility repo-local HuggingFace embedding API](documentations/procedures/local-huggingface-embedding-api.md)
- [Manage LM Studio setup for agent-basics](documentations/procedures/lmstudio-setup-control.md)

## References

- None yet.
