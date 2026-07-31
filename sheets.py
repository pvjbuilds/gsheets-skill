"""Reusable Google Sheets read/write core. Works on any sheet the OAuth user owns.

Auth: gspread's cached OAuth (credentials.json -> browser consent once -> authorized_user.json).
Scope is `spreadsheets` only -- no Drive access, so sheets are addressed by ID, never by name.
"""

import gspread
from gspread.urls import SPREADSHEETS_API_V4_BASE_URL
from gspread.utils import a1_range_to_grid_range

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_client = None


def client():
    global _client
    if _client is None:
        _client = gspread.oauth(scopes=SCOPES)
    return _client


def create(title, tab_names=None):
    """Create a new spreadsheet in the user's My Drive root. Returns id + url.

    Uses the Sheets API's own create method, not Drive's, so this works under the
    spreadsheets-only scope. Cost of that: the new file lands in My Drive root and
    can't be placed in a folder from here -- move it in the Drive UI.
    """
    body = {"properties": {"title": title}}
    if tab_names:
        body["sheets"] = [{"properties": {"title": t}} for t in tab_names]
    r = client().http_client.request(
        "post", SPREADSHEETS_API_V4_BASE_URL, json=body
    ).json()
    return {"id": r["spreadsheetId"], "url": r["spreadsheetUrl"],
            "tabs": [s["properties"]["title"] for s in r["sheets"]]}


def tabs(sheet_id):
    """List tab names with their row/col extents."""
    return [
        {"title": w.title, "rows": w.row_count, "cols": w.col_count}
        for w in client().open_by_key(sheet_id).worksheets()
    ]


def read(sheet_id, tab, a1=None, formulas=False):
    """Return rows as {row: <1-indexed sheet row>, values: [...]}.

    Row numbers come back so callers can locate a row by its label and then
    address it in a write without re-deriving the offset.

    formulas=True returns the underlying formula text (e.g. "=SUM(B2:B9)")
    instead of the computed value -- use it before editing a calculated sheet,
    so you can see what you are about to overwrite.
    """
    ws = client().open_by_key(sheet_id).worksheet(tab)
    render = "FORMULA" if formulas else "FORMATTED_VALUE"
    if a1:
        rows = ws.get(a1, value_render_option=render)
        first = int("".join(c for c in a1.split(":")[0] if c.isdigit()) or 1)
    else:
        rows = ws.get_values(value_render_option=render)
        first = 1
    return [{"row": first + i, "values": r} for i, r in enumerate(rows)]


def _worksheets(sh, items):
    """Map tab title -> worksheet, raising if any item names a tab that isn't there.

    Validating everything up front is the point: a typo'd tab name must abort the
    whole call rather than apply to the tabs that happened to be spelled right.
    """
    known = {w.title: w for w in sh.worksheets()}
    for i in items:
        if i["tab"] not in known:
            raise ValueError(f"no such tab: {i['tab']!r} (have: {sorted(known)})")
    return known


def _by_tab(sh, items, build):
    """Validate tab names, then group items per tab."""
    _worksheets(sh, items)
    grouped = {}
    for i in items:
        grouped.setdefault(i["tab"], []).append(build(i))
    return grouped


def write(sheet_id, updates):
    """Batch-write cells. updates: [{"tab": str, "a1": "B7", "value": str}, ...]

    One API call per tab. Writing to a merged range's anchor cell (e.g. B7 of a
    merged B7:D7) updates the merge without breaking it.
    """
    sh = client().open_by_key(sheet_id)
    by_tab = _by_tab(sh, updates, lambda u: {"range": u["a1"], "values": [[u["value"]]]})
    for tab, batch in by_tab.items():
        sh.worksheet(tab).batch_update(batch, value_input_option="USER_ENTERED")
    return {"cells_written": len(updates), "tabs": sorted(by_tab)}


def format_cells(sheet_id, formats):
    """Apply cell formatting. Values are untouched -- this only changes rendering.

    formats: [{"tab": str, "a1": "B2:B20", "format": {...}}, ...] where format is a
    Sheets API CellFormat. Common ones (see README for more):

      currency  {"numberFormat": {"type": "CURRENCY", "pattern": "₹#,##0.00"}}
      percent   {"numberFormat": {"type": "PERCENT",  "pattern": "0.0%"}}
      date      {"numberFormat": {"type": "DATE",     "pattern": "dd-mmm-yyyy"}}
      bold      {"textFormat": {"bold": True}}
      fill      {"backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}}

    Keys merge, so a header can be bold AND filled in one format dict.
    """
    sh = client().open_by_key(sheet_id)
    by_tab = _by_tab(sh, formats, lambda f: {"range": f["a1"], "format": f["format"]})
    for tab, batch in by_tab.items():
        sh.worksheet(tab).batch_format(batch)
    return {"ranges_formatted": len(formats), "tabs": sorted(by_tab)}


def freeze(sheet_id, tab, rows=1, cols=0):
    """Freeze header rows and/or leading columns so they stay put when scrolling."""
    rows, cols = int(rows), int(cols)  # CLI hands these over as strings
    client().open_by_key(sheet_id).worksheet(tab).freeze(rows, cols)
    return {"tab": tab, "frozen_rows": rows, "frozen_cols": cols}


def conditional(sheet_id, rules, replace=False):
    """Add conditional-format rules: colour cells based on what's in them.

    rules: [{"tab": str, "a1": "B2:B99",
             "condition": <BooleanCondition>, "format": <CellFormat>}, ...]

      negative red   {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]}
      status match   {"type": "TEXT_EQ",     "values": [{"userEnteredValue": "AMBER"}]}
      over budget    {"type": "CUSTOM_FORMULA",
                      "values": [{"userEnteredValue": "=$C2>$B2"}]}

    CUSTOM_FORMULA is the general case -- it can reference other columns, and its
    row references are relative to the range's first row.

    replace=True clears existing rules on the touched tabs first. Leave it False
    (default) to add to what's there; re-running the same call then stacks
    duplicate rules, which is the usual way a sheet ends up with nine copies.
    """
    sh = client().open_by_key(sheet_id)
    known = _worksheets(sh, rules)
    reqs = []
    if replace:
        meta = {s["properties"]["sheetId"]: len(s.get("conditionalFormats", []))
                for s in sh.fetch_sheet_metadata()["sheets"]}
        for tab in {r["tab"] for r in rules}:
            sid = known[tab].id
            # delete back-to-front: each removal renumbers the rules after it
            reqs += [{"deleteConditionalFormatRule": {"sheetId": sid, "index": i}}
                     for i in reversed(range(meta.get(sid, 0)))]
    for r in rules:
        reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [a1_range_to_grid_range(r["a1"], known[r["tab"]].id)],
            "booleanRule": {"condition": r["condition"], "format": r["format"]},
        }}})
    sh.batch_update({"requests": reqs})
    return {"rules_added": len(rules), "replaced": replace,
            "tabs": sorted({r["tab"] for r in rules})}


def append(sheet_id, tab, rows):
    """Append rows below the last non-empty row. rows: [[cell, cell, ...], ...]"""
    ws = client().open_by_key(sheet_id).worksheet(tab)
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return {"rows_appended": len(rows), "tab": tab}


if __name__ == "__main__":
    import json
    import sys

    fn = {"create": create, "tabs": tabs, "read": read, "write": write,
          "append": append, "format": format_cells,
          "freeze": freeze, "conditional": conditional}[sys.argv[1]]
    args = [json.loads(a) if a[:1] in "[{" or a in ("true", "false") else a
            for a in sys.argv[2:]]
    print(json.dumps(fn(*args), indent=2, ensure_ascii=False))
