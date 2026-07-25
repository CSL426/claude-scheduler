#!/usr/bin/env bash

set -euo pipefail

REPOSITORY="CSL426/claude-scheduler"
VERSION="${CLAUDE_SCHEDULER_VERSION:-latest}"
BIN_DIR="${CLAUDE_SCHEDULER_BIN_DIR:-$HOME/.local/bin}"

kernel="$(uname -s)"
architecture="$(uname -m)"

case "$kernel" in
    Linux)
        platform="linux"
        ;;
    Darwin)
        platform="macos"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \
            "\$script = irm 'https://raw.githubusercontent.com/$REPOSITORY/main/install.ps1'; & ([scriptblock]::Create(\$script))"
        exit
        ;;
    *)
        echo "Unsupported operating system: $kernel" >&2
        exit 1
        ;;
esac

case "$architecture" in
    x86_64|amd64)
        architecture="x86_64"
        ;;
    arm64|aarch64)
        architecture="arm64"
        ;;
    *)
        echo "Unsupported architecture: $architecture" >&2
        exit 1
        ;;
esac

if [[ "$platform" == "linux" && "$architecture" != "x86_64" ]]; then
    echo "Linux $architecture releases are not available." >&2
    exit 1
fi

asset="claude-scheduler-$platform-$architecture"
if [[ "$VERSION" == "latest" ]]; then
    release_url="https://github.com/$REPOSITORY/releases/latest/download"
else
    release_url="https://github.com/$REPOSITORY/releases/download/$VERSION"
fi

temporary_dir="$(mktemp -d)"
cleanup() {
    if [[ -d "$temporary_dir" ]]; then
        rm -r -- "$temporary_dir"
    fi
}
trap cleanup EXIT

curl -fsSL "$release_url/$asset" -o "$temporary_dir/$asset"
curl -fsSL "$release_url/$asset.sha256" -o "$temporary_dir/$asset.sha256"

expected="$(awk '{print $1}' "$temporary_dir/$asset.sha256")"
if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$temporary_dir/$asset" | awk '{print $1}')"
else
    actual="$(shasum -a 256 "$temporary_dir/$asset" | awk '{print $1}')"
fi

if [[ "$expected" != "$actual" ]]; then
    echo "Checksum verification failed for $asset." >&2
    exit 1
fi

mkdir -p "$BIN_DIR"
install -m 0755 "$temporary_dir/$asset" "$BIN_DIR/claude-scheduler"

echo "Installed claude-scheduler to $BIN_DIR/claude-scheduler"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo "Add $BIN_DIR to PATH to run claude-scheduler from a new shell."
        ;;
esac
if [[ "${CLAUDE_SCHEDULER_SKIP_SETUP:-0}" != "1" ]]; then
    "$BIN_DIR/claude-scheduler" install
fi
