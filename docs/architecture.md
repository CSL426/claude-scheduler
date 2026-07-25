# Architecture

## Shared core

`claude_scheduler.config` owns the validated machine-local configuration.
`claude_scheduler.runner` resolves Claude CLI and executes it with an argument
list rather than a shell command. Credentials remain entirely under Claude
CLI's control.

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

PyInstaller builds a native executable on each target operating system. Shell
and PowerShell installers download the matching GitHub Release asset, verify
its SHA-256 file, and create scheduled tasks without requiring a source
checkout or a local Python installation.
