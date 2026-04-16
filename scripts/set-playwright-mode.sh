#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# set-playwright-mode.sh
# Reads playwright.mode from UAF_POC/config.json and patches ~/.claude.json.
# Usage:
#   ./scripts/set-playwright-mode.sh              # uses config.json value
#   ./scripts/set-playwright-mode.sh headed       # override: force headed
#   ./scripts/set-playwright-mode.sh headless     # override: force headless
# After running, restart Claude Code for the change to take effect.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config.json"
CLAUDE_JSON="$HOME/.claude.json"

# ── Resolve target mode ───────────────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
  MODE="$1"
else
  if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required to read config.json" >&2
    exit 1
  fi
  MODE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['playwright']['mode'])")
fi

if [[ "$MODE" != "headed" && "$MODE" != "headless" ]]; then
  echo "Error: mode must be 'headed' or 'headless', got: '$MODE'" >&2
  exit 1
fi

# ── Build args list ───────────────────────────────────────────────────────────
if [[ "$MODE" == "headed" ]]; then
  NEW_ARGS='["@playwright/mcp@latest", "--headed"]'
else
  NEW_ARGS='["@playwright/mcp@latest"]'
fi

# ── Patch ~/.claude.json ──────────────────────────────────────────────────────
python3 - <<PYEOF
import json, sys

claude_path = "$CLAUDE_JSON"
new_args    = $NEW_ARGS

with open(claude_path, 'r') as f:
    data = json.load(f)

data.setdefault('mcpServers', {})
data['mcpServers']['playwright'] = {
    'command': 'npx',
    'args': new_args
}

with open(claude_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Patched ~/.claude.json — playwright MCP args: {new_args}")
PYEOF

# ── Also update config.json so it stays in sync ───────────────────────────────
python3 - <<PYEOF
import json

config_path = "$CONFIG_FILE"
mode        = "$MODE"

with open(config_path, 'r') as f:
    cfg = json.load(f)

cfg['playwright']['mode'] = mode

with open(config_path, 'w') as f:
    json.dump(cfg, f, indent=2)

print(f"Updated config.json — playwright.mode = '{mode}'")
PYEOF

echo ""
echo "✔  Playwright MCP is now set to: $MODE"
echo "   Restart Claude Code for the change to take effect."
