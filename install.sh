#!/usr/bin/env bash

set -euo pipefail

REPOSITORY="${CCS_REPOSITORY:-${CLAUDE_SCHEDULER_REPOSITORY:-CSL426/claude-scheduler}}"
VERSION="${CCS_VERSION:-${CLAUDE_SCHEDULER_VERSION:-latest}}"
BIN_DIR="${CCS_BIN_DIR:-${CLAUDE_SCHEDULER_BIN_DIR:-$HOME/.local/bin}}"
LOCAL_BINARY="${CCS_BINARY_PATH:-}"
SKIP_SETUP="${CCS_SKIP_SETUP:-${CLAUDE_SCHEDULER_SKIP_SETUP:-0}}"
SKIP_COMPLETION="${CCS_SKIP_COMPLETION:-0}"

step() { printf '\033[0;36m▸\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m⚠\033[0m %s\n' "$*"; }
fail() { printf '\033[0;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

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

asset="ccs-$platform-$architecture"
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

download_asset() {
    local selected_asset="$1"
    curl -fsSL "$release_url/$selected_asset" \
        -o "$temporary_dir/$selected_asset" &&
        curl -fsSL "$release_url/$selected_asset.sha256" \
            -o "$temporary_dir/$selected_asset.sha256"
}

if [[ -n "$LOCAL_BINARY" ]]; then
    [[ -f "$LOCAL_BINARY" ]] || fail "Local binary not found: $LOCAL_BINARY"
    source_binary="$LOCAL_BINARY"
else
    if ! download_asset "$asset"; then
        fail "Could not download a CC Scheduler release for this platform."
    fi
    source_binary="$temporary_dir/$asset"
    expected="$(awk '{print $1}' "$source_binary.sha256")"
    if command -v sha256sum >/dev/null 2>&1; then
        actual="$(sha256sum "$source_binary" | awk '{print $1}')"
    elif command -v shasum >/dev/null 2>&1; then
        actual="$(shasum -a 256 "$source_binary" | awk '{print $1}')"
    else
        fail "sha256sum or shasum is required to verify the download."
    fi

    [[ "$expected" == "$actual" ]] ||
        fail "Checksum verification failed for $asset."
fi

mkdir -p "$BIN_DIR"
destination="$BIN_DIR/ccs"
staged_binary="$destination.new.$$"
install -m 0755 "$source_binary" "$staged_binary"
mv -f "$staged_binary" "$destination"

install_bash_completion() {
    local completion_root completion_dir completion_file staged_completion
    [[ "$SKIP_COMPLETION" == "1" ]] && return
    completion_root="${BASH_COMPLETION_USER_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/bash-completion}"
    completion_root="${completion_root%%:*}"
    completion_dir="$completion_root/completions"
    completion_file="$completion_dir/ccs.bash"
    staged_completion="$completion_file.new.$$"
    mkdir -p "$completion_dir"
    if "$destination" completion bash > "$staged_completion"; then
        mv -f "$staged_completion" "$completion_file"
        rm -f -- \
            "$completion_dir/claude-scheduler.bash" \
            "$completion_dir/claude-scheduler.exe.bash"
        step "Installed Bash completion: $completion_file"
        step "Activate now without reopening:" \
            "export PATH=\"$BIN_DIR:\$PATH\" && hash -r &&" \
            "source <(\"$destination\" completion bash)"
    else
        rm -f -- "$staged_completion"
        warn "Shell completion could not be installed."
    fi
}

step "Installed CC Scheduler to $destination"
install_bash_completion
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        warn "$BIN_DIR is not in PATH — add: export PATH=\"$BIN_DIR:\$PATH\""
        ;;
esac
if [[ "$SKIP_SETUP" != "1" ]]; then
    "$destination" install
fi

legacy_destination="$BIN_DIR/claude-scheduler"
if [[ "$SKIP_SETUP" == "1" ]] &&
    [[ -f "$legacy_destination" || -L "$legacy_destination" ]]; then
    warn "Preserved $legacy_destination because scheduler setup was skipped."
    warn "Run ccs install to migrate the schedule and remove the legacy command."
elif [[ -f "$legacy_destination" || -L "$legacy_destination" ]]; then
    rm -f -- "$legacy_destination"
    step "Removed legacy command: $legacy_destination"
fi
