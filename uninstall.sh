#!/usr/bin/env bash
# uninstall.sh
# Removes cc-weekly-status.py and strips the statusLine entry.
# Leaves unrelated entries in ~/.claude/settings.json untouched.
# Usage: bash uninstall.sh

set -e

SETTINGS="$HOME/.claude/settings.json"

rm -f "$HOME/.local/bin/cc-weekly-status.py"

[ ! -f "$SETTINGS" ] && { echo "No settings.json — nothing to unpatch."; exit 0; }

cp "$SETTINGS" "$SETTINGS.bak.$(date +%s)"

python3 - "$SETTINGS" << 'EOF'
import json, sys
p = sys.argv[1]
s = json.loads(open(p).read())
s.pop('statusLine', None)
open(p, 'w').write(json.dumps(s, indent=2))
print(f'✓ Removed statusLine from {p}')
EOF

echo "Backup written next to $SETTINGS"
