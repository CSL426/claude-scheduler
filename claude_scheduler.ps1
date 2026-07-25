param(
    [switch]$Setup,
    [switch]$Test
)

$command = if ($Setup) {
    "install"
} else {
    "run"
}

$executable = Get-Command ccs -ErrorAction SilentlyContinue
if ($executable) {
    & $executable.Source $command
} elseif ($Setup) {
    Write-Error (
        "ccs is not installed. Run: " +
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
