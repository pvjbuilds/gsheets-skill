---
name: gsheets
description: "Create, read, and edit Google Sheets in your own Google Drive — new trackers from scratch, or bulk/structured edits to an existing sheet (updating rows, filling columns, appending entries, applying a batch of changes). Use whenever a Google Sheet or a sheet ID/URL is named, or when the user asks to build a spreadsheet, log data into one, or apply changes to one. Not for local .xlsx files."
---

# gsheets

Google Sheets read/write via `$HOME/.gsheets-mcp/`. OAuth token is
cached globally at `~/.config/gspread/`, so this works from any directory.

**Requires a session with Bash access to the machine where it is installed.** A cloud sandbox session has
neither the venv nor the token — say so and stop rather than improvising.

Preflight: `ls ~/.config/gspread/authorized_user.json`. Missing → the backend isn't
authorised on this machine; point the user at `~/.gsheets-mcp/README.md` and stop.

## Commands

```bash
P="$HOME/.gsheets-mcp/.venv/bin/python"; S="$HOME/.gsheets-mcp/sheets.py"
"$P" "$S" create "My Tracker" '["Dashboard","Log"]'
"$P" "$S" tabs   <sheet_id>
"$P" "$S" read   <sheet_id> "Dashboard" [A1:H40]
"$P" "$S" write  <sheet_id> '[{"tab":"Dashboard","a1":"B7","value":"x"}]'
"$P" "$S" append <sheet_id> "Log" '[["row","of","cells"]]'
"$P" "$S" format <sheet_id> '[{"tab":"Log","a1":"B2:B99","format":{"numberFormat":{"type":"CURRENCY","pattern":"₹#,##0.00"}}}]'
"$P" "$S" freeze <sheet_id> "Log" 1
"$P" "$S" conditional <sheet_id> '[{"tab":"Log","a1":"B2:B99","condition":{"type":"NUMBER_LESS","values":[{"userEnteredValue":"0"}]},"format":{"backgroundColor":{"red":1,"green":0.8,"blue":0.8}}}]'
```

`read` returns `{row, values}` with 1-indexed sheet rows. `write` batches one API
call per tab and validates every tab name before writing anything. Sheet ID is the
long string in the URL between `/d/` and `/edit`.

## Procedure for edits

1. **Read the target tabs first.** Always. Never write to a row number taken from a
   spec, a previous session, or an uploaded doc — layouts drift.
2. **Resolve each change to a real cell** by finding its row label in the read output.
   If a label isn't found, **stop and ask** — never write to a best-guess row.
3. **Dry-run** when there are more than ~10 cells: print tab/cell/value and eyeball it.
4. **Write** as one batch.
5. **Read back and confirm** each change, by name, in the reply.

For anything over ~20 changes, write a throwaway Python file that imports `sheets`,
builds the update list, and supports `--dry-run` — rather than hand-rolling a giant
JSON argument on the command line.

## Writing formulas

Writes use `USER_ENTERED`, so any value starting with `=` becomes a **live formula**,
exactly as if typed into the cell. Everything Sheets supports works: `SUM`, `SUMIF`,
`XLOOKUP`, `QUERY`, `ARRAYFORMULA`, `IFERROR`, absolute refs (`$B$4`), cross-tab refs
(`='Log'!B2`), whole-column ranges.

```json
[{"tab":"Summary","a1":"B10","value":"=SUM(Expenses!C2:C)"},
 {"tab":"Summary","a1":"C10","value":"=IFERROR(B10/$B$20,0)"}]
```

When building a calculated sheet: lay out the data tab first, then write the formula
cells referencing it. Read back with `formulas=True` to confirm the formula text, and
without it to confirm the computed result is sane — a formula that returns `#REF!` or
`0` still "wrote successfully".

## Formatting

`format` changes how cells render; it never touches their values or formulas.
`[{"tab": str, "a1": "B2:B20", "format": <CellFormat>}, ...]`, batched per tab like
`write`. Formats persist through later value writes, so format a sheet once.

```json
{"numberFormat": {"type":"CURRENCY","pattern":"₹#,##0.00"}}
{"numberFormat": {"type":"PERCENT", "pattern":"0.0%"}}
{"numberFormat": {"type":"DATE",    "pattern":"dd-mmm-yyyy"}}
{"textFormat":   {"bold":true}}
{"backgroundColor": {"red":0.85,"green":0.89,"blue":0.95}}
{"horizontalAlignment":"RIGHT"}
```

Keys combine in one dict — a header row is usually `textFormat` + `backgroundColor`.
Colours are 0–1 floats, not 0–255. Currency cells hold plain numbers (`1200`), never
`"₹1,200"` — the format does the rendering; a currency string would be dead text.
Building a sheet: values and formulas first, then one `format` call at the end.

## Frozen rows and conditional formatting

`freeze` pins header rows/columns: `freeze <id> "Log" 1` freezes the top row.

`conditional` colours cells by their contents —
`[{"tab", "a1", "condition": <BooleanCondition>, "format": <CellFormat>}, ...]`:

```json
{"type":"NUMBER_LESS",   "values":[{"userEnteredValue":"0"}]}
{"type":"TEXT_EQ",       "values":[{"userEnteredValue":"Overdue"}]}
{"type":"NUMBER_BETWEEN","values":[{"userEnteredValue":"0"},{"userEnteredValue":"100"}]}
{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":"=$C2>$B2"}]}
```

`CUSTOM_FORMULA` is the general case: it can reference other columns, and its row
number must be the range's **first** row (`$C2` for a range starting at row 2) — the
rule is then applied relative to each row. Lock the column with `$`, not the row.

**Rules stack.** Running the same call twice leaves two identical rules. Pass
`replace=true` when re-applying rules to a sheet you've styled before — it clears
existing rules on those tabs first. That also deletes rules the user made by hand, so
default to appending unless you're re-running your own setup.

**Still not supported:** data validation/dropdowns, charts, named ranges, column
widths, protected ranges. Say so rather than implying they were applied.

## Rules

- Don't restructure: no renaming tabs, reordering rows, changing headers, deleting rows.
- Don't touch cells no one asked about.
- **Merged cells:** write to the anchor cell (`B` of a merged `B:D`). Preserves the merge.
- **Formulas:** `read` returns computed values; add `true` as the 4th arg (or
  `formulas=True`) to see formula text instead. Do that before editing any calculated
  sheet, and never overwrite a formula cell without flagging it first.
- **New rows:** if the sheet has pre-numbered or blank rows inside the table, fill them
  in place — `append` goes below the *last* non-empty row, which may sit under footnotes.
- Report anything skipped or half-applied, explicitly, at the end.

## Scope limits

`spreadsheets` scope only — no Drive. Consequences:
- Sheets are addressed by **ID**, never searched by name. Ask for the ID or URL.
- New sheets land in **My Drive root**; they can't be filed into a folder from here.
- Cannot delete, rename, share, or list files.
