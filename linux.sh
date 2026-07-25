#!/usr/bin/env bash

set -euo pipefail

if command -v ccs >/dev/null 2>&1; then
    exec ccs install
fi

echo "ccs is not installed." >&2
echo "Run: python -m pip install --editable \"$(dirname "$0")\"" >&2
exit 1
