#!/usr/bin/env bash

set -euo pipefail

if command -v claude-scheduler >/dev/null 2>&1; then
    exec claude-scheduler install
fi

echo "claude-scheduler is not installed." >&2
echo "Run: python -m pip install --editable \"$(dirname "$0")\"" >&2
exit 1
