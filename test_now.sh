#!/bin/bash

echo "Testing Claude Scheduler Now"
echo "============================="
echo
echo "Current time: $(date '+%Y-%m-%d %H:%M:%S')"
echo

echo "Running bash script..."
bash "$(dirname "$0")/claude_scheduler.sh" test

echo
echo "Test completed!"
echo "Check the log file: scheduled_task.log"
echo

read -p "Press Enter to continue..."