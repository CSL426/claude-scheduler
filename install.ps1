# Install the standalone CC Scheduler release. Python is not required.
#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Repository = if ($env:CCS_REPOSITORY) {
    $env:CCS_REPOSITORY
} elseif ($env:CLAUDE_SCHEDULER_REPOSITORY) {
    $env:CLAUDE_SCHEDULER_REPOSITORY
} else {
    'CSL426/claude-scheduler'
}
$Version = if ($env:CCS_VERSION) {
    $env:CCS_VERSION
} elseif ($env:CLAUDE_SCHEDULER_VERSION) {
    $env:CLAUDE_SCHEDULER_VERSION
} else {
    'latest'
}
$UserHome = [Environment]::GetFolderPath('UserProfile')
$BinDir = if ($env:CCS_BIN_DIR) {
    $env:CCS_BIN_DIR
} elseif ($env:CLAUDE_SCHEDULER_BIN_DIR) {
    $env:CLAUDE_SCHEDULER_BIN_DIR
} else {
    Join-Path $UserHome '.local\bin'
}
$LocalBinary = if ($env:CCS_BINARY_PATH) { $env:CCS_BINARY_PATH } else { $null }
$SkipSetup = $env:CCS_SKIP_SETUP -eq '1' -or $env:CLAUDE_SCHEDULER_SKIP_SETUP -eq '1'
$SkipCompletion = $env:CCS_SKIP_COMPLETION -eq '1'

function Write-Step([string]$Message) { Write-Host "* $Message" -ForegroundColor Cyan }
function Write-Warn([string]$Message) { Write-Host "! $Message" -ForegroundColor Yellow }
function Fail([string]$Message) { Write-Host "x $Message" -ForegroundColor Red; exit 1 }

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $Encoding = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($Path, $Content, $Encoding)
}

function Install-Binary([string]$Source, [string]$Destination) {
    $Attempts = 50
    for ($Attempt = 1; $Attempt -le $Attempts; $Attempt++) {
        try {
            Copy-Item -LiteralPath $Source -Destination $Destination -Force
            return
        }
        catch {
            if ($Attempt -eq $Attempts) { throw }
            Start-Sleep -Milliseconds 200
        }
    }
}

function Read-ProfileText([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
    $Bytes = [IO.File]::ReadAllBytes($Path)
    if ($Bytes.Length -eq 0) { return '' }
    if (
        $Bytes.Length -ge 3 -and
        $Bytes[0] -eq 0xef -and
        $Bytes[1] -eq 0xbb -and
        $Bytes[2] -eq 0xbf
    ) {
        return (New-Object System.Text.UTF8Encoding($true)).GetString(
            $Bytes,
            3,
            $Bytes.Length - 3
        )
    }
    if ($Bytes.Length -ge 2 -and $Bytes[0] -eq 0xff -and $Bytes[1] -eq 0xfe) {
        return [Text.Encoding]::Unicode.GetString($Bytes, 2, $Bytes.Length - 2)
    }
    if ($Bytes.Length -ge 2 -and $Bytes[0] -eq 0xfe -and $Bytes[1] -eq 0xff) {
        return [Text.Encoding]::BigEndianUnicode.GetString(
            $Bytes,
            2,
            $Bytes.Length - 2
        )
    }
    try {
        return (New-Object System.Text.UTF8Encoding($false, $true)).GetString(
            $Bytes
        )
    }
    catch {
        return [Text.Encoding]::Default.GetString($Bytes)
    }
}

function Update-CompletionProfile(
    [string]$ProfilePath,
    [string]$CompletionPath
) {
    New-Item -ItemType Directory -Force -Path (
        Split-Path -Parent $ProfilePath
    ) | Out-Null
    $MarkerStart = '# >>> ccs completion >>>'
    $MarkerEnd = '# <<< ccs completion <<<'
    $QuotedCompletionPath = $CompletionPath.Replace("'", "''")
    $Block = "$MarkerStart`r`n. '$QuotedCompletionPath'`r`n$MarkerEnd"
    $ProfileText = Read-ProfileText $ProfilePath
    $StartIndex = $ProfileText.IndexOf(
        $MarkerStart,
        [StringComparison]::Ordinal
    )
    $EndIndex = if ($StartIndex -ge 0) {
        $ProfileText.IndexOf(
            $MarkerEnd,
            $StartIndex,
            [StringComparison]::Ordinal
        )
    } else {
        -1
    }
    if ($StartIndex -ge 0 -and $EndIndex -ge 0) {
        $SuffixIndex = $EndIndex + $MarkerEnd.Length
        $UpdatedProfile = (
            $ProfileText.Substring(0, $StartIndex) +
            $Block +
            $ProfileText.Substring($SuffixIndex)
        )
    } else {
        $Separator = if (
            $ProfileText -and -not $ProfileText.EndsWith("`n")
        ) {
            "`r`n"
        } else {
            ''
        }
        $UpdatedProfile = $ProfileText + $Separator + $Block + "`r`n"
    }
    $Encoding = New-Object System.Text.UTF8Encoding($true)
    [IO.File]::WriteAllText($ProfilePath, $UpdatedProfile, $Encoding)
}

function Install-Completions([string]$Executable) {
    if ($SkipCompletion) { return }
    try {
        $BashCompletion = @(& $Executable completion bash)
        if ($LASTEXITCODE -ne 0) {
            throw 'Bash completion generation failed.'
        }
        $PowerShellCompletion = @(& $Executable completion powershell)
        if ($LASTEXITCODE -ne 0) {
            throw 'PowerShell completion generation failed.'
        }
    }
    catch {
        Write-Warn "Shell completion could not be installed: $($_.Exception.Message)"
        return
    }

    $BashCompletionDir = Join-Path (
        $UserHome
    ) '.local\share\bash-completion\completions'
    New-Item -ItemType Directory -Force -Path $BashCompletionDir | Out-Null
    $BashText = ($BashCompletion -join "`n") + "`n"
    Write-Utf8NoBom (Join-Path $BashCompletionDir 'ccs.bash') $BashText
    Remove-Item -LiteralPath (
        Join-Path $BashCompletionDir 'claude-scheduler.bash'
    ) -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (
        Join-Path $BashCompletionDir 'claude-scheduler.exe.bash'
    ) -Force -ErrorAction SilentlyContinue

    $CompletionDir = Join-Path $UserHome '.local\share\ccs'
    New-Item -ItemType Directory -Force -Path $CompletionDir | Out-Null
    $PowerShellCompletionPath = Join-Path $CompletionDir 'completion.ps1'
    Write-Utf8NoBom $PowerShellCompletionPath (
        ($PowerShellCompletion -join "`r`n") + "`r`n"
    )
    Update-CompletionProfile (
        $PROFILE.CurrentUserAllHosts
    ) $PowerShellCompletionPath
    Write-Step 'Installed Bash and PowerShell completions; restart the terminal to load them.'
}

if (-not [Environment]::Is64BitOperatingSystem) {
    Fail 'Only 64-bit Windows is supported.'
}

$Asset = 'ccs-windows-x86_64.exe'
$Destination = Join-Path $BinDir 'ccs.exe'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

if ($LocalBinary) {
    if (-not (Test-Path -LiteralPath $LocalBinary -PathType Leaf)) {
        Fail "Local binary not found: $LocalBinary"
    }
    Write-Step 'Installing local standalone binary'
    Install-Binary $LocalBinary $Destination
} else {
    $ReleaseUrl = if ($Version -eq 'latest') {
        "https://github.com/$Repository/releases/latest/download"
    } else {
        "https://github.com/$Repository/releases/download/$Version"
    }
    $TemporaryDir = Join-Path (
        [IO.Path]::GetTempPath()
    ) ("ccs-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $TemporaryDir | Out-Null
    try {
        $Download = Join-Path $TemporaryDir $Asset
        $Checksum = "$Download.sha256"
        Invoke-WebRequest -UseBasicParsing -Uri (
            "$ReleaseUrl/$Asset"
        ) -OutFile $Download
        Invoke-WebRequest -UseBasicParsing -Uri (
            "$ReleaseUrl/$Asset.sha256"
        ) -OutFile $Checksum
        $Expected = (
            (Get-Content -LiteralPath $Checksum -Raw).Trim() -split '\s+'
        )[0].ToLowerInvariant()
        $Actual = (
            Get-FileHash -LiteralPath $Download -Algorithm SHA256
        ).Hash.ToLowerInvariant()
        if ($Expected -ne $Actual) {
            Fail "Checksum verification failed for $Asset."
        }
        Install-Binary $Download $Destination
    }
    finally {
        Remove-Item -LiteralPath $TemporaryDir `
            -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$PathEntries = @($UserPath -split ';' | Where-Object { $_ })
if ($PathEntries -notcontains $BinDir) {
    $UpdatedPath = (@($PathEntries) + $BinDir) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $UpdatedPath, 'User')
}
if (($env:Path -split ';') -notcontains $BinDir) {
    $env:Path = "$BinDir;$env:Path"
}

Write-Step "Installed CC Scheduler to $Destination"
Install-Completions $Destination
if (-not $SkipSetup) {
    & $Destination install
    if ($LASTEXITCODE -ne 0) {
        throw "Scheduler setup failed with exit code $LASTEXITCODE."
    }
}

$LegacyNames = @(
    'claude-scheduler.exe',
    'claude-scheduler',
    'claude-scheduler.cmd'
)
foreach ($LegacyName in $LegacyNames) {
    $LegacyDestination = Join-Path $BinDir $LegacyName
    if (
        $SkipSetup -and
        (Test-Path -LiteralPath $LegacyDestination -PathType Leaf)
    ) {
        Write-Warn "Preserved $LegacyDestination because scheduler setup was skipped."
        Write-Warn 'Run ccs install to migrate the schedule and remove the legacy command.'
    } elseif (Test-Path -LiteralPath $LegacyDestination -PathType Leaf) {
        Remove-Item -LiteralPath $LegacyDestination -Force
        Write-Step "Removed legacy command: $LegacyDestination"
    }
}
