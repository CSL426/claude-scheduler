param(
    [switch]$Setup,
    [switch]$Test
)

$command = if ($Setup) {
    "install"
} else {
    "run"
}

$executable = Get-Command claude-scheduler -ErrorAction SilentlyContinue
if ($executable) {
    & $executable.Source $command
} elseif ($Setup) {
    Write-Error (
        "claude-scheduler is not installed. Run: " +
        "python -m pip install --editable `"$PSScriptRoot`""
    )
    exit 1
} else {
    Push-Location $PSScriptRoot
    try {
        & python -m claude_scheduler $command
    }
    finally {
        Pop-Location
    }
}

exit $LASTEXITCODE
