#!/usr/bin/env bash

set -euo pipefail

if command -v claude-scheduler >/dev/null 2>&1; then
    exec claude-scheduler run
fi

cd "$(dirname "$0")"
exec python -m claude_scheduler run
