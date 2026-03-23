# Windows Scheduled Task Script - Claude Auto Reset
# Runs every 5 hours to match Claude's reset cycle

param(
    [switch]$Setup,
    [switch]$Test
)

# =========================== Configuration ===========================
# Command to execute (modify to your actual command)
$commandToRun = "claude -p 'hi'"

# Daily execution times (24-hour format: HH:mm)
# Set to run every 5 hours to match Claude's reset cycle
$scheduleTimes = @(
    "07:30",  # Start of workday
    "12:30",  # Midday (7:30 + 5 hours)
    "17:30",  # Afternoon (12:30 + 5 hours)
    "22:30"   # Evening (17:30 + 5 hours)
)

# Log file path - use absolute path for scheduled tasks
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) {
    # Fallback method if MyInvocation doesn't work
    $scriptDir = Split-Path -Parent $PSCommandPath
}
if (-not $scriptDir) {
    # Another fallback for scheduled tasks - try to find script in current directory
    $currentDir = Get-Location
    $scriptInCurrentDir = Join-Path $currentDir "claude_scheduler.ps1"
    if (Test-Path $scriptInCurrentDir) {
        $scriptDir = $currentDir
    } else {
        # Last resort - assume the script is in the working directory
        $scriptDir = $currentDir
    }
}
$logFile = Join-Path $scriptDir "scheduled_task.log"
# Note: Write-Log will be called after the function is defined below

# =========================== Functions ===========================
function Write-Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $message"
    Write-Host $logMessage

    try {
        # Try to write to log file
        Add-Content -Path $logFile -Value $logMessage -Encoding UTF8 -ErrorAction Stop
    }
    catch {
        # If log file write fails, try alternative methods
        try {
            # Method 1: Use Out-File
            $logMessage | Out-File -FilePath $logFile -Append -Encoding UTF8
        }
        catch {
            try {
                # Method 2: Use .NET StreamWriter
                $stream = [System.IO.StreamWriter]::new($logFile, $true, [System.Text.Encoding]::UTF8)
                $stream.WriteLine($logMessage)
                $stream.Close()
            }
            catch {
                # Method 3: Use Set-Content (overwrite mode, but append manually)
                $existingContent = ""
                if (Test-Path $logFile) {
                    $existingContent = Get-Content $logFile -Raw
                }
                $newContent = $existingContent + "`r`n" + $logMessage
                Set-Content -Path $logFile -Value $newContent -Encoding UTF8
            }
        }
    }
}

function Test-ShouldRun {
    $currentTime = Get-Date -Format "HH:mm"
    return $scheduleTimes -contains $currentTime
}

function Execute-Command {
    try {
        Write-Log "Starting command execution: $commandToRun"

        # Define temporary output files
        $outputFile = [System.IO.Path]::GetTempFileName()
        $errorFile = [System.IO.Path]::GetTempFileName()

        # Check if claude command exists
        Write-Log "Checking if claude command is available..."
        $claudeCheck = Start-Process -FilePath "cmd.exe" -ArgumentList "/c where claude 2>nul" -NoNewWindow -Wait -PassThru
        if ($claudeCheck.ExitCode -eq 0) {
            Write-Log "Claude command found in PATH"
        } else {
            Write-Log "Claude command NOT found in PATH - checking common locations..."

            # Check common Claude installation locations
            $claudePaths = @(
                "$env:USERPROFILE\AppData\Local\Programs\Claude\Claude.exe",
                "$env:USERPROFILE\AppData\Local\Claude\Claude.exe",
                "C:\Program Files\Claude\Claude.exe",
                "C:\Program Files (x86)\Claude\Claude.exe"
            )

            $claudeFound = $false
            foreach ($path in $claudePaths) {
                if (Test-Path $path) {
                    Write-Log "Found Claude at: $path"
                    $commandToRun = "`"$path`" -p 'hi'"
                    $claudeFound = $true
                    break
                }
            }

            if (-not $claudeFound) {
                Write-Log "Claude executable not found in common locations"
                Write-Log "Please check Claude installation or update the command path in the script"
            }
        }

        # Execute command with output capture
        Write-Log "Executing command: $commandToRun"
        $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c $commandToRun" -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $outputFile -RedirectStandardError $errorFile

        # Option 2: Show window (uncomment the line below if you want to see the command window)
        # $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c $commandToRun" -Wait -PassThru

        # Read output and integrate into main log
        if (Test-Path $outputFile) {
            $output = Get-Content $outputFile -Raw
            if ($output) {
                Write-Log "Command output: $output"
            } else {
                Write-Log "Command produced no output"
            }
            # Clean up temporary output file
            Remove-Item $outputFile -Force -ErrorAction SilentlyContinue
        }

        # Read error and integrate into main log
        if (Test-Path $errorFile) {
            $errorOutput = Get-Content $errorFile -Raw
            if ($errorOutput) {
                Write-Log "Command error: $errorOutput"
            }
            # Clean up temporary error file
            Remove-Item $errorFile -Force -ErrorAction SilentlyContinue
        }

        if ($process.ExitCode -eq 0) {
            Write-Log "Command executed successfully"
        } else {
            Write-Log "Command execution failed with exit code: $($process.ExitCode)"
            Write-Log "This usually means the claude command was not found or failed to execute"
        }
    }
    catch {
        Write-Log "Error executing command: $($_.Exception.Message)"
    }
}

function Setup-ScheduledTasks {
    Write-Log "Setting up Windows Task Scheduler..."

    $scriptPath = Join-Path $scriptDir "claude_scheduler.ps1"
    Write-Log "Using script path: $scriptPath"
    $taskName = "ClaudeAutoReset"

    # Delete existing tasks if they exist
    try {
        schtasks /delete /tn $taskName /f 2>$null
        Write-Log "Deleted existing scheduled tasks"
    } catch {
        # Task doesn't exist, ignore error
    }

    # Create tasks for each time slot
    for ($i = 0; $i -lt $scheduleTimes.Length; $i++) {
        $time = $scheduleTimes[$i]
        $timeFormatted = $time.Replace(":", "")
        $taskNameWithTime = "Claude_$timeFormatted"

        # Delete existing specific time tasks
        try {
            schtasks /delete /tn $taskNameWithTime /f 2>$null
        } catch {
            # Ignore errors
        }

        # Create new scheduled task
        try {
            # Check if running as administrator
            $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
            Write-Log "Running as administrator: $isAdmin"

            # Use a simple command without complex quoting - with hidden window
            $action = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
            $createCommand = "schtasks /create /sc daily /st $time /tn $taskNameWithTime /tr `"$action`" /f"
            Write-Log "Action command: $action"
            Write-Log "Executing: $createCommand"

            # Execute the command and capture output
            $result = Invoke-Expression $createCommand 2>&1
            Write-Log "Command result: $result"
            Write-Log "LASTEXITCODE: $LASTEXITCODE"

            if ($LASTEXITCODE -eq 0) {
                Write-Log "Created scheduled task: $taskNameWithTime (daily at $time)"
                Write-Log "Task creation result: $result"
            } else {
                Write-Log "Failed to create task: $taskNameWithTime - Exit code: $LASTEXITCODE"
                Write-Log "Error output: $result"

                # Try a simpler method - with hidden window
                Write-Log "Trying simpler method..."
                $simpleAction = "cmd.exe /c powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File $scriptPath"
                $simpleCommand = "schtasks /create /sc daily /st $time /tn $taskNameWithTime /tr `"$simpleAction`" /f"
                Write-Log "Simple command: $simpleCommand"
                $simpleResult = Invoke-Expression $simpleCommand 2>&1
                Write-Log "Simple result: $simpleResult"
                Write-Log "Simple LASTEXITCODE: $LASTEXITCODE"
            }
        } catch {
            Write-Log "Exception creating task: $taskNameWithTime - $($_.Exception.Message)"
        }
    }

    Write-Log "Task Scheduler setup completed"
}

# =========================== Main Program ===========================
Write-Log "=== Claude Auto Reset Script Started ==="
Write-Log "Resolved script directory: $scriptDir"
Write-Log "Script location: $scriptDir"
Write-Log "Current working directory: $(Get-Location)"
Write-Log "Current time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# Check if setup mode
if ($Setup) {
    Setup-ScheduledTasks
    exit
}

# Check if test mode or command should be executed
if ($Test) {
    Write-Log "Test mode: Force executing command regardless of schedule..."
    Execute-Command
} elseif (Test-ShouldRun) {
    Write-Log "Current time matches schedule, starting execution..."
    Execute-Command
} else {
    Write-Log "Current time is not in schedule, skipping execution"
    Write-Log "Scheduled times: $($scheduleTimes -join ', ')"
    Write-Log "Current time check: $(Get-Date -Format 'HH:mm')"
}

Write-Log "=== Script Execution Completed ==="
