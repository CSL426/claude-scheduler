#!/bin/bash

# Linux Scheduled Task Script - Claude Auto Reset
# Runs every 5 hours to match Claude's reset cycle

# =========================== Configuration ===========================
# Command to execute (modify to your actual command)
COMMAND_TO_RUN="claude -p 'hi'"

# Timezone setting (optional, defaults to system timezone)
# Set to "Asia/Taipei" for UTC+8, or leave empty to use system timezone
TIMEZONE="Asia/Taipei"

# Daily execution times (24-hour format: HH:MM)
# Set to run every 5 hours to match Claude's reset cycle
SCHEDULE_TIMES=(
    "07:30"  # Start of workday
    "12:30"  # Midday (7:30 + 5 hours)
    "17:30"  # Afternoon (12:30 + 5 hours)
    "22:30"  # Evening (17:30 + 5 hours)
)

# Log file path - use absolute path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/scheduled_task.log"

# =========================== Functions ===========================
write_log() {
    local timestamp
    if [[ -n "$TIMEZONE" ]]; then
        timestamp=$(TZ="$TIMEZONE" date '+%Y-%m-%d %H:%M:%S')
    else
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    fi
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

test_should_run() {
    local current_time
    if [[ -n "$TIMEZONE" ]]; then
        current_time=$(TZ="$TIMEZONE" date '+%H:%M')
    else
        current_time=$(date '+%H:%M')
    fi

    for time in "${SCHEDULE_TIMES[@]}"; do
        if [[ "$current_time" == "$time" ]]; then
            return 0
        fi
    done
    return 1
}

execute_command() {
    write_log "Starting command execution: $COMMAND_TO_RUN"

    # Create temporary files
    local output_file error_file
    output_file=$(mktemp)
    error_file=$(mktemp)

    # Execute command with output capture
    if eval "$COMMAND_TO_RUN" > "$output_file" 2> "$error_file"; then
        # Read output if available
        if [[ -s "$output_file" ]]; then
            local output
            output=$(cat "$output_file")
            write_log "Command output: $output"
        else
            write_log "Command produced no output"
        fi

        # Read error if available
        if [[ -s "$error_file" ]]; then
            local error_output
            error_output=$(cat "$error_file")
            write_log "Command error: $error_output"
        fi

        write_log "Command executed successfully"
        
        # Clean up temporary files
        rm -f "$output_file" "$error_file"
        return 0
    else
        local exit_code=$?
        write_log "Command execution failed with exit code: $exit_code"

        # Read error output on failure
        if [[ -s "$error_file" ]]; then
            local error_output
            error_output=$(cat "$error_file")
            write_log "Command error: $error_output"
        fi

        # Clean up temporary files
        rm -f "$output_file" "$error_file"
        return $exit_code
    fi
}

setup_cron() {
    write_log "Setting up Linux cron jobs..."

    local script_path
    script_path=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")

    # Remove existing cron jobs for this script
    crontab -l 2>/dev/null | grep -v "$script_path" | crontab -

    # Add new cron jobs
    for time in "${SCHEDULE_TIMES[@]}"; do
        local hour minute
        hour=$(echo "$time" | cut -d: -f1)
        minute=$(echo "$time" | cut -d: -f2)

        # Create cron job with timezone support
        if [[ -n "$TIMEZONE" ]]; then
            # Set TZ in the cron command for compatibility with macOS and Linux
            (crontab -l 2>/dev/null; echo "$minute $hour * * * TZ=$TIMEZONE $script_path") | crontab -
        else
            # Use system timezone
            (crontab -l 2>/dev/null; echo "$minute $hour * * * $script_path") | crontab -
        fi

        write_log "Added cron job: $time daily"
    done

    write_log "Cron setup completed"
    write_log "Current cron jobs:"
    crontab -l | tee -a "$LOG_FILE"
}

# =========================== Main Program ===========================
write_log "=== Claude Auto Reset Script Started ==="

# Check if setup mode
if [[ "$1" == "setup" ]]; then
    setup_cron
    exit 0
fi

# Check if test mode or command should be executed  
if [[ "$1" == "test" ]]; then
    write_log "Test mode: Force executing command regardless of schedule..."
    execute_command
elif test_should_run; then
    write_log "Current time matches schedule, starting execution..."
    execute_command
else
    write_log "Current time is not in schedule, skipping execution"
    current_time=""
    if [[ -n "$TIMEZONE" ]]; then
        current_time=$(TZ="$TIMEZONE" date '+%H:%M')
    else
        current_time=$(date '+%H:%M')
    fi
    write_log "Scheduled times: ${SCHEDULE_TIMES[*]}"
    write_log "Current time check: $current_time"
fi

write_log "=== Script Execution Completed ==="
