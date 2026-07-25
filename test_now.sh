#!/usr/bin/env bash

set -euo pipefail

if command -v ccs >/dev/null 2>&1; then
    exec ccs run
fi

cd "$(dirname "$0")"
exec python -m claude_scheduler run
