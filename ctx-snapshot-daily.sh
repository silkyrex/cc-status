#!/bin/bash
# Daily ctx snapshot + Discord ping if wall hit

set -e

LOG=$(python3 /Users/rzhu/.local/bin/ctx-snapshot.py 2>&1)
echo "$LOG"

source /Users/rzhu/.config/credentials/discord-reminders.env

if echo "$LOG" | grep -q "WALL HIT"; then
    MSG="⚠️ ctx snapshot: $LOG"
else
    MSG="ctx snapshot: $LOG"
fi

curl -s -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "User-Agent: ctx-snapshot/1.0" \
  -d "{\"content\": \"$MSG\"}"
