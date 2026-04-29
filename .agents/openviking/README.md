# OpenViking

This directory contains project-local OpenViking integration files for agent-basics.

Keep OpenViking configuration, setup state, backups, exports, and merge sessions under this directory when OpenViking's documented configuration model allows project-local placement.

Use these environment variables before running OpenViking commands for this repo:

```bash
export PATH="$PWD/.agents/openviking/venv/bin:$PATH"
export OPENVIKING_CONFIG_FILE="$PWD/.agents/openviking/ov.conf"
export OPENVIKING_CLI_CONFIG_FILE="$PWD/.agents/openviking/ovcli.conf"
```

