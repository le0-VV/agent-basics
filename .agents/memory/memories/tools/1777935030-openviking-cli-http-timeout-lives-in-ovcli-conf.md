---
record_kind: memory
ov_category: tools
title: OpenViking CLI HTTP timeout lives in ovcli.conf
status: active
created: 1777935030
updated: 1777935301
tags: [openviking, ovcli, timeout]
summary: OpenViking CLI HTTP operations need a long `~/.openviking/ovcli.conf` timeout for slow local model processing.
source_paths: []
requires_human_review: false
---

# OpenViking CLI HTTP timeout lives in ovcli.conf

Project: agent-basics

## Content

OpenViking server-side VLM timeout in ~/.openviking/ov.conf does not control the ov CLI HTTP client timeout. The CLI reads ~/.openviking/ovcli.conf timeout, which defaults to 60 seconds and can make local LM Studio skill ingestion fail even when --timeout is 86400. agent-basics ov write-default-config must write ovcli.conf with timeout 86400, and setup-macos.sh must ensure both ov.conf and ovcli.conf exist.
