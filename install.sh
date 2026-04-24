#!/usr/bin/env bash
# install.sh
# Installs cc-weekly-status.py and sets the statusLine entry.
# Usage: bash install.sh

set -e

if ! command -v python3 &>/dev/null; then
  echo "python3 not found."
  exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=${PY_VER%%.*}
PY_MINOR=${PY_VER##*.}
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
  echo "python3 >= 3.9 required (found $PY_VER). zoneinfo is stdlib since 3.9."
  exit 1
fi

SETTINGS="$HOME/.claude/settings.json"
STATUS_SCRIPT="$HOME/.local/bin/cc-weekly-status.py"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$HOME/.local/bin" "$HOME/.claude"
[ -f "$STATUS_SCRIPT" ] && [ ! -L "$STATUS_SCRIPT" ] && rm "$STATUS_SCRIPT"
ln -sf "$REPO_DIR/cc-weekly-status.py" "$STATUS_SCRIPT"
chmod +x "$REPO_DIR/cc-weekly-status.py"
echo "✓ Status script symlinked at $STATUS_SCRIPT -> $REPO_DIR/cc-weekly-status.py"

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak.$(date +%s)"
else
  echo '{}' > "$SETTINGS"
fi

python3 - "$SETTINGS" "$STATUS_SCRIPT" << 'EOF'
import json, sys

settings_path, status_script = sys.argv[1], sys.argv[2]
with open(settings_path) as f:
    s = json.load(f)

s['statusLine'] = {'type': 'command', 'command': status_script, 'refreshInterval': 60}

with open(settings_path, 'w') as f:
    json.dump(s, f, indent=2)

print(f'✓ settings.json updated at {settings_path}')
EOF

echo ""
echo "Install complete. Restart Claude Code."
