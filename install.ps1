param(
    [string]$Version = $(if ($env:CLAUDE_SCHEDULER_VERSION) {
        $env:CLAUDE_SCHEDULER_VERSION
    } else {
        "latest"
    }),
    [string]$BinDir = $(if ($env:CLAUDE_SCHEDULER_BIN_DIR) {
        $env:CLAUDE_SCHEDULER_BIN_DIR
    } else {
        Join-Path $HOME ".local\bin"
    })
)

$ErrorActionPreference = "Stop"
$repository = "ac-Spark/claude-scheduler"
$asset = "claude-scheduler-windows-x86_64.exe"

if ($Version -eq "latest") {
    $releaseUrl = "https://github.com/$repository/releases/latest/download"
} else {
    $releaseUrl = "https://github.com/$repository/releases/download/$Version"
}

$temporaryDir = Join-Path ([System.IO.Path]::GetTempPath()) (
    "claude-scheduler-" + [System.Guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $temporaryDir | Out-Null

try {
    $download = Join-Path $temporaryDir $asset
    $checksum = "$download.sha256"
    Invoke-WebRequest "$releaseUrl/$asset" -OutFile $download -UseBasicParsing
    Invoke-WebRequest "$releaseUrl/$asset.sha256" -OutFile $checksum -UseBasicParsing

    $expected = (Get-Content $checksum -Raw).Trim().Split()[0].ToLowerInvariant()
    $actual = (Get-FileHash $download -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($expected -ne $actual) {
        throw "Checksum verification failed for $asset."
    }

    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    $destination = Join-Path $BinDir "claude-scheduler.exe"
    Copy-Item $download $destination -Force

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $pathEntries = @($userPath -split ";" | Where-Object { $_ })
    if ($pathEntries -notcontains $BinDir) {
        $updatedPath = (@($pathEntries) + $BinDir) -join ";"
        [Environment]::SetEnvironmentVariable("Path", $updatedPath, "User")
    }
    if (($env:Path -split ";") -notcontains $BinDir) {
        $env:Path = "$BinDir;$env:Path"
    }

    Write-Host "Installed claude-scheduler to $destination"
    if ($env:CLAUDE_SCHEDULER_SKIP_SETUP -ne "1") {
        & $destination install
        if ($LASTEXITCODE -ne 0) {
            throw "Scheduler setup failed with exit code $LASTEXITCODE."
        }
    }
}
finally {
    Remove-Item $temporaryDir -Recurse -Force -ErrorAction SilentlyContinue
}
