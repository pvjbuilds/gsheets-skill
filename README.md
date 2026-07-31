# gsheets — Google Sheets for Claude

A Claude skill that lets any Claude session **create, read, and edit Google Sheets**
in your own Drive — from plain English, with guardrails that stop it from mangling
your spreadsheet.

```
You:    "Here's my sheet: <sheet URL>. Set the Q3 row's status to Approved,
         and add a new row for the migration project."

Claude: reads the sheet → finds those rows by name → shows you what it'll write
        → writes it in one batch → reads it back and confirms each change.
```

Install once per machine. Works from every project directory afterwards.

---

## What's in the box

| Piece | What it is |
|---|---|
| **The skill** (`SKILL.md`) | Instructions Claude loads when a Google Sheet comes up. Holds the working procedure and the safety rules. |
| **The library** (`sheets.py`) | ~80 lines over [`gspread`](https://docs.gspread.org/). Also a CLI. This is what actually talks to Google. |
| **The MCP server** (`server.py`) | Exposes the library as five tools to Claude sessions that prefer tools over shell commands. Optional. |
| **The installer** (`install.sh`) | Puts everything in the right place on a new machine. |

The skill is the instructions; the library is the hands. You need both, and
`install.sh` sets up both.

## Install

**New machine? Read [SETUP.md](SETUP.md) — it walks through the whole thing including
Google credentials.** The short version:

```bash
git clone https://github.com/Prygozhyn/gsheets-skill.git
cd gsheets-skill
./install.sh
```

## What it can do

| Operation | Example ask |
|---|---|
| **Create** | "Build me a reading tracker with tabs for Books, Notes, and Stats" |
| **Read** | "What's in the Summary tab?" |
| **Write** | "Set the Q3 row's status to Approved" |
| **Append** | "Add a row for the migration project" |
| **Bulk edit** | "Apply all 24 changes in this document to the sheet" |

Give Claude the sheet **URL or ID** and describe the change in normal language. The
sheet ID is the long string in the URL between `/d/` and `/edit`.

## How it behaves (and why)

Spreadsheets are easy to silently corrupt — one off-by-one row and you've overwritten
real data with no undo trail. The skill encodes a procedure that prevents the common
failure modes:

1. **Reads the sheet before writing.** Never trusts row numbers from a document, a
   plan, or an earlier conversation. Layouts drift; reading is cheap.
2. **Resolves every change to a real cell** by finding its row *label*, not its position.
3. **Stops and asks** if a label isn't found, instead of guessing a nearby row.
4. **Dry-runs** anything over ~10 cells so you can eyeball it first.
5. **Writes in one batch per tab** — faster, and it can't half-apply. A typo in a tab
   name aborts the whole batch before a single cell changes.
6. **Reads back and confirms** each change by name.

It also refuses to restructure things on its own: no renaming tabs, no reordering or
deleting rows, no touching cells nobody asked about. Merged cells are written through
their anchor cell so the merge survives, and formula cells are flagged rather than
silently overwritten.

## Scope and limits

Authentication uses the **`spreadsheets` scope only — no Google Drive access.** That's
deliberate: this thing can touch spreadsheets you point it at and nothing else in your
account. The trade-offs that follow from it:

- **Sheets are addressed by ID.** It can't search your Drive by name — give it the URL.
- **New sheets land in My Drive root.** It can't file them into a folder; move them yourself.
- **It cannot delete, rename, or share anything.** No destructive operations exist in the API surface.

Two more limits worth knowing:

- **Needs a session with shell access to the machine where it's installed.** The code
  and your Google token live on disk. A cloud sandbox session has neither — the skill
  detects this and says so rather than improvising.
- **Google Sheets only, not `.xlsx` files.** Different format, different tooling.

## Using it without Claude

The library is a normal CLI:

```bash
P=~/.gsheets-mcp/.venv/bin/python; S=~/.gsheets-mcp/sheets.py
"$P" "$S" create "My Tracker" '["Dashboard","Log"]'
"$P" "$S" tabs   <sheet_id>
"$P" "$S" read   <sheet_id> "Dashboard"          # optional 4th arg: "A1:H40"
"$P" "$S" write  <sheet_id> '[{"tab":"Dashboard","a1":"B7","value":"done"}]'
"$P" "$S" append <sheet_id> "Log" '[["2026-08-01","entry"]]'
```

`read` returns `{row, values}` with **1-indexed sheet row numbers**, so you can find a
row by its label and address it in a write without counting.

Or import it:

```python
import sys; sys.path.insert(0, os.path.expanduser("~/.gsheets-mcp"))
import sheets
sheets.write(sheet_id, [{"tab": "Dashboard", "a1": "B7", "value": "done"}])
```

For big change sets, write a throwaway script that builds the update list and supports
`--dry-run`, rather than a giant JSON string on the command line.

## MCP server (optional)

If you want Claude to call these as tools rather than shell commands, add to a
project's `.mcp.json` (expand `~` to your real home path — `.mcp.json` won't):

```json
{"mcpServers":{"google-sheets":{
  "command":"/Users/YOU/.gsheets-mcp/.venv/bin/python",
  "args":["/Users/YOU/.gsheets-mcp/server.py"]}}}
```

Tools: `sheets_create`, `sheets_tabs`, `sheets_read`, `sheets_write`, `sheets_append`.
Restart the session to pick it up. The skill works fine without this.

## Self-check

```bash
~/.gsheets-mcp/.venv/bin/python ~/.gsheets-mcp/test_sheets.py   # prints "ok"
```

Runs offline against a fake sheet — no network, no credentials needed. Covers row
numbering, per-tab batching, and that a bad tab name aborts before anything is written.

## A note on what's not in this repo

No credentials, no tokens, no sheet IDs, no spreadsheet content. `.gitignore` blocks
`*.json` and `apply_*.py` so none of that can drift in later. Your Google credentials
live only in `~/.config/gspread/` on each machine.

## Licence

Personal tooling. Use it however you like.
