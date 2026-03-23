#!/bin/bash

# Linux Claude Scheduler Setup Script

echo "Claude Auto Reset Task Setup Tool"
echo "=================================="

echo "Setting up Linux cron jobs..."
echo "Will create the following cron jobs:"
echo "- Daily 07:30 (start of workday)"
echo "- Daily 12:30 (midday)"
echo "- Daily 17:30 (afternoon)"
echo "- Daily 22:30 (evening)"
echo ""

# Make script executable
chmod +x "$(dirname "$0")/claude_scheduler.sh"

# Run setup
"$(dirname "$0")/claude_scheduler.sh" setup

echo ""
echo "Setup completed!"
echo ""
echo "Script will automatically execute 'claude -p hi' at:"
echo "- Daily 07:30 (start of workday)"
echo "- Daily 12:30 (midday)"
echo "- Daily 17:30 (afternoon)"
echo "- Daily 22:30 (evening)"
echo ""
echo "Timezone: Asia/Taipei (UTC+8)"
echo "This matches Claude's 5-hour reset cycle"
echo "Log file: scheduled_task.log"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
