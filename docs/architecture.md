# Architecture

## Shared core

`claude_scheduler.config` owns the validated machine-local configuration.
`claude_scheduler.runner` resolves Claude CLI and executes it with an argument
list rather than a shell command. Credentials remain entirely under Claude
CLI's control.

Claude path resolution has two explicit modes. `auto` stores a stable launcher
path and follows Claude Code upgrades, while `explicit` uses only the path
selected by the user. Configuration written before the mode field existed is
treated as `auto`; the previous version-specific native path is retained only
as a fallback until it can be migrated to the stable launcher.

## Platform boundary

The scheduler backend is selected at runtime:

- Linux: a marked block in the user's crontab
- macOS: `com.ac-spark.claude-scheduler.plist` in `~/Library/LaunchAgents`
- Windows: user tasks named `ClaudeScheduler_HHMM`

Each backend owns only entries with the project's marker, label, or task-name
prefix. Installation replaces those entries and preserves unrelated scheduler
state.

Migration recognizes the previous unmarked `claude_scheduler.sh` cron command
and the previous Windows `Claude_HHMM` task names. macOS removes the legacy
cron entry before installing its LaunchAgent.

## Distribution

PyInstaller builds the native `ccs` or `ccs.exe` executable on each target
operating system. Shell and PowerShell installers download the matching GitHub
Release asset, verify its SHA-256 file, install shell completion, and create
scheduled tasks without requiring a source checkout or a local Python
installation. Existing configuration paths and scheduler ownership identifiers
remain stable across the executable rename.
