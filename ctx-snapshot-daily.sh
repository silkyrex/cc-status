#!/bin/bash
# Daily ctx snapshot + Discord ping if wall hit

set -e

LOG=$(python3 /Users/rzhu/.local/bin/ctx-snapshot.py 2>&1)
echo "$LOG"

source /Users/rzhu/.config/credentials/discord-channels.env
WEBHOOK_URL="${OPS_HEARTBEAT_WEBHOOK_URL:-${DISCORD_WEBHOOK_URL:-}}"

if echo "$LOG" | grep -q "WALL HIT"; then
    MSG="⚠️ ctx snapshot: $LOG"
else
    MSG="ctx snapshot: $LOG"
fi

[ -z "$WEBHOOK_URL" ] && exit 0

curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "User-Agent: ctx-snapshot/1.0" \
  -d "{\"content\": \"$MSG\"}"
