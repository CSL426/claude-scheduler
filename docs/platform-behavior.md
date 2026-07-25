# Platform behavior

Schedule times use the operating system's local timezone.

Linux writes a delimited block to the user's existing crontab. Removing the
scheduler deletes only that block.

macOS writes one LaunchAgent containing multiple calendar intervals. Standard
output and error from launchd itself are kept in the platform state directory.

Windows creates one user-level daily task per configured time. Task creation
uses argv-based subprocess calls and does not require administrator privileges
or a PowerShell execution-policy change.

The configured Claude executable path is machine-local. A run first uses that
path when it still exists, then falls back to resolving `claude` from `PATH`.
Windows npm `.cmd` shims are not executed through the command shell; the runner
resolves the associated Claude CLI JavaScript file and invokes it with Node.
