#!/usr/bin/env bash
# Installs the gsheets skill + its Google Sheets backend on this machine.
# Always installs to ~/.gsheets-mcp so the skill's paths are identical everywhere,
# no matter where you cloned the repo.
set -euo pipefail

DEST="$HOME/.gsheets-mcp"
SKILLS="$HOME/.claude/skills/gsheets"
SRC="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$DEST" "$SKILLS"
cp "$SRC"/{sheets.py,server.py,test_sheets.py,README.md,SETUP.md} "$DEST/"
cp "$SRC/SKILL.md" "$SKILLS/"

[ -d "$DEST/.venv" ] || python3 -m venv "$DEST/.venv"
"$DEST/.venv/bin/pip" install -q --upgrade pip
"$DEST/.venv/bin/pip" install -q gspread google-auth-oauthlib "mcp[cli]"
"$DEST/.venv/bin/python" "$DEST/test_sheets.py"

echo "installed -> $DEST"
echo "skill     -> $SKILLS/SKILL.md"

if [ ! -f "$HOME/.config/gspread/credentials.json" ]; then
  cat <<'EOF'

NEXT: this machine has no Google credentials yet -- one more step.

  Easiest:  copy BOTH files from ~/.config/gspread/ on a machine that already
            works, into ~/.config/gspread/ here. Nothing else needed.

  Otherwise: follow Step 2, Path B in SETUP.md (5 min, one browser visit).

Full walkthrough incl. troubleshooting: ~/.gsheets-mcp/SETUP.md
EOF
fi

cat <<'EOF'

Optional, for MCP tools inside a project: add to that project's .mcp.json --
{"mcpServers":{"google-sheets":{"command":"~/.gsheets-mcp/.venv/bin/python",
 "args":["~/.gsheets-mcp/server.py"]}}}
(expand ~ to your home path -- .mcp.json does not do it for you)
EOF
