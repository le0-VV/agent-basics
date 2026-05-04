---
id: procedure-1777827387-openviking-gateway
type: procedure
title: Use the agent-basics OpenViking gateway
status: planned
created: 1777827387
updated: 1777827387
tags: [agent-basics, openviking, mcp, memory, resources, skills]
summary: Route agent memory, documentation, resource, and skill work through the repo-aware agent-basics OpenViking gateway.
---

# Use the agent-basics OpenViking gateway

## When To Use

Use this whenever an agent needs prior project context, durable memory recording, documentation/resource ingestion, reusable skill registration, or OpenViking health checks in an agent-basics repository.

## Steps

1. Resolve the repository root before calling the gateway.
2. Prefer `agent-basics mcp` when the agent client supports MCP.
3. Configure the MCP server with the repository root as the working directory.
4. Search prior context through the OpenViking-backed MCP search tool or `agent-basics ov search "<query>"` before answering vague or history-dependent requests.
5. Record durable decisions, facts, preferences, gotchas, events, procedures, and useful findings through the OpenViking-backed MCP record tool or `agent-basics ov record`.
6. Add important documentation or reference material with `agent-basics ov add-resource <path-or-url>`.
7. Add reusable workflows with `agent-basics ov add-skill <path>`.
8. After instruction, documentation, memory, or skill files change, run `agent-basics ov ingest-changed`.
9. Run `agent-basics ov doctor` before relying on OpenViking if setup, provider configuration, or ingest state is uncertain.

## Codex Desktop Configuration

In Settings -> MCP servers -> Connect to a custom MCP, use these fields:

- Name: `agent-basics`
- Transport: `STDIO`
- Command to launch: `agent-basics`
- Arguments: `mcp`
- Environment variables: only provider secret variables named by `.agents/config.toml` or user-level OpenViking config
- Environment variable passthrough: the same provider secret variables, only when needed
- Working directory: absolute path to the repository root

For this repository:

- Command to launch: `agent-basics`
- Arguments: `mcp`
- Working directory: `/Users/leonardw/Projects/agent-basics`

## Verification

Run `agent-basics ov doctor` or call the MCP doctor tool. The result should report OpenViking installation, repo-local config, provider health, and ingest status.

## Related

- `Agents.md`
- `.agents/AGENT-BASICS.md`
- `ROADMAP.md`
