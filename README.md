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
| **The library** (`sheets.py`) | ~190 lines over [`gspread`](https://docs.gspread.org/). Also a CLI. This is what actually talks to Google. |
| **The MCP server** (`server.py`) | Exposes the library as eight tools to Claude sessions that prefer tools over shell commands. Optional. |
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
| **Format** | "Make the header bold and show column B as currency" |
| **Highlight** | "Freeze the header row and turn negative amounts red" |
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

## Formulas

Writes use `USER_ENTERED`, so a value beginning with `=` becomes a live formula, same
as typing it in. `SUM`, `SUMIF`, `XLOOKUP`, `QUERY`, `ARRAYFORMULA`, absolute refs,
cross-tab refs — all of it works, and Claude writes the formula for you from a plain
description ("total the expenses column, then show each category as a % of it").

Read formulas back instead of their results:

```bash
"$P" "$S" read <sheet_id> "Summary" "A1:D20" true    # formula text, not values
```

## Formatting

`format` changes how cells render without touching their values:

```bash
"$P" "$S" format <sheet_id> '[
  {"tab":"Summary","a1":"A1:D1",  "format":{"textFormat":{"bold":true},
                                            "backgroundColor":{"red":0.85,"green":0.89,"blue":0.95}}},
  {"tab":"Summary","a1":"B2:B99", "format":{"numberFormat":{"type":"CURRENCY","pattern":"₹#,##0.00"}}},
  {"tab":"Summary","a1":"C2:C99", "format":{"numberFormat":{"type":"PERCENT","pattern":"0.0%"}}}
]'
```

Turns `1200` into `₹1,200.00` and `0.2727` into `27.3%`. Any
[CellFormat](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#cellformat)
field works — number/currency/date formats, bold and italic, text and background
colour (0–1 floats), alignment, wrapping. Keys combine in one dict.

Formats persist through later value writes, so you format a sheet once and every
subsequent edit stays styled. Keep currency cells as plain numbers — the format does
the rendering.

## Frozen headers and conditional formatting

Freeze the top row so headers stay put while scrolling:

```bash
"$P" "$S" freeze <sheet_id> "Summary" 1        # rows; optional 4th arg = columns
```

Colour cells by what's in them — negatives red, overdue rows amber, over-budget rows
flagged against another column:

```bash
"$P" "$S" conditional <sheet_id> '[
  {"tab":"Summary","a1":"C2:C99",
   "condition":{"type":"NUMBER_LESS","values":[{"userEnteredValue":"0"}]},
   "format":{"backgroundColor":{"red":1,"green":0.8,"blue":0.8},"textFormat":{"bold":true}}},
  {"tab":"Summary","a1":"A2:A99",
   "condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":"=$C2>$B2"}]},
   "format":{"backgroundColor":{"red":1,"green":0.95,"blue":0.8}}}
]'
```

Any Sheets
[BooleanCondition](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#booleancondition)
works — `NUMBER_LESS`, `NUMBER_BETWEEN`, `TEXT_EQ`, `TEXT_CONTAINS`, `DATE_BEFORE`,
`BLANK`, and `CUSTOM_FORMULA` for anything else. In a custom formula, use the range's
**first** row number (`$C2` for a range starting at row 2); Sheets applies it relative
to each row from there.

**Rules stack.** Running the same call twice gives you two identical rules. Add
`replace` to clear existing rules on the touched tabs first — handy when iterating on a
sheet's styling, but it also removes rules you created by hand.

**Still not supported:** data validation and dropdowns, charts, named ranges, column
widths, protected ranges.

## Scope and limits

Authentication uses the **`spreadsheets` scope only — no Google Drive access.** That's
deliberate: this thing can touch spreadsheets you point it at and nothing else in your
account. The trade-offs that follow from it:

- **Sheets are addressed by ID.** It can't search your Drive by name — give it the URL.
- **New sheets land in My Drive root.** It can't file them into a folder; move them yourself.
- **It cannot delete or rename files, tabs, or rows, and cannot share anything.** The only
  destructive operation anywhere is `conditional --replace`, which clears conditional-format
  rules on the tabs it touches. Nothing can remove data.

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
"$P" "$S" format <sheet_id> '[{"tab":"Log","a1":"B2:B99","format":{"textFormat":{"bold":true}}}]'
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

Tools: `sheets_create`, `sheets_tabs`, `sheets_read`, `sheets_write`, `sheets_append`,
`sheets_format`, `sheets_freeze`, `sheets_conditional`.
Restart the session to pick it up. The skill works fine without this.

## Self-check

```bash
~/.gsheets-mcp/.venv/bin/python ~/.gsheets-mcp/test_sheets.py   # prints "ok"
```

Runs offline against a fake sheet — no network, no credentials needed. Covers row
numbering, per-tab batching, A1→GridRange conversion, the back-to-front rule deletes,
and that a bad tab name aborts before anything is written.

## A note on what's not in this repo

No credentials, no tokens, no sheet IDs, no spreadsheet content. `.gitignore` blocks
`*.json` and `apply_*.py` so none of that can drift in later. Your Google credentials
live only in `~/.config/gspread/` on each machine.

## Self-improvement

Every run ends by asking itself three questions: did a step fail or need a workaround, did I
correct or reject anything meaningful, did it discover something a future run should know.
If the answer to any of them is yes, it proposes an edit to `SKILL.md`. I accept or reject
it — nothing changes on its own.

The point is that keeping the skill correct becomes a side effect of using it, instead of a
separate chore that never gets done. Adapted from the self-improvement block in Remy
Gaskell's Multiplayer Skills Guide (2026).

## Licence

Personal tooling. Use it however you like.
