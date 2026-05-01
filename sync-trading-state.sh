#!/bin/bash
# sync-trading-state.sh -- pull /tmp/trading.state.json from droplet to local
# /tmp for the cc-status weekly-status slot. Runs every 60s via launchd.
#
# Only active during trading.service hours (6:00 AM - 14:00 PT M-F) since
# the bot only writes the state file when it's running. Outside that window,
# we delete the local file so the status line slot collapses immediately
# instead of waiting for the 5-min staleness threshold.
#
# trading.service writes the state file every 60s (run.py tick loop).
# This script copies it down. Single ssh per minute, ~1s per call.

set -uo pipefail

SRC_HOST="momentum"
SRC_PATH="/tmp/trading.state.json"
DST_PATH="/tmp/trading.state.json"
TMP_PATH="/tmp/trading.state.json.new"

# Trading window guard: 6:00 AM - 14:00 PT M-F.
HOUR=$(date +%-H)
DAY=$(date +%u)   # 1=Mon ... 7=Sun

if [[ "$DAY" -gt 5 ]] || [[ "$HOUR" -lt 6 ]] || [[ "$HOUR" -ge 14 ]]; then
    rm -f "$DST_PATH"
    exit 0
fi

ssh -o ConnectTimeout=3 \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=no \
    "$SRC_HOST" \
    "cat $SRC_PATH 2>/dev/null" \
    > "$TMP_PATH" 2>/dev/null

if [[ -s "$TMP_PATH" ]]; then
    mv "$TMP_PATH" "$DST_PATH"
else
    rm -f "$TMP_PATH"
fi
