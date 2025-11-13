#!/usr/bin/env bash
# live_app_log.sh
# Description: Show the last 100 lines of app.log and follow new logs in real-time

LOG_FILE="app.log"

# Check if the log file exists
if [[ -f "$LOG_FILE" ]]; then
  echo "Displaying the last 100 lines of $LOG_FILE and following new logs..."
  echo "Press Ctrl + C to exit."
  echo "----------------------------------------------"
  
  # Show last 100 lines and keep following
  tail -n 100 -f "$LOG_FILE"
else
  echo "Error: $LOG_FILE not found!"
  exit 1
fi
