#!/bin/bash
# sync-trading-state.sh -- pull /tmp/trading.state.json from droplet to local
# /tmp for the cc-status weekly-status slot. Runs every 60s via launchd.
#
# trading.service writes the state file every 60s (run.py tick loop).
# This script copies it down. Single ssh per minute, ~1s per call.
#
# Silent fail: if droplet is unreachable, the local file just goes stale and
# the status line slot collapses (cc-weekly-status.py treats >5min as missing).

set -uo pipefail

SRC_HOST="momentum"
SRC_PATH="/tmp/trading.state.json"
DST_PATH="/tmp/trading.state.json"
TMP_PATH="/tmp/trading.state.json.new"

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
