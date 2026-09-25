"""MCP server exposing the sheets core to any Claude session. stdio transport."""

import functools

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import sheets

mcp = MCPServer(
    "google-sheets",
    instructions=(
        "Read and write any Google Sheet the authenticated user owns. "
        "Sheets are addressed by their ID (the long string in the sheet URL). "
        "To change a row, sheets_read the tab first, locate the row by its label "
        "in the returned values, then sheets_write using the row number returned."
    ),
)


def tool(description):
    """mcp.tool, but a failure reaches Claude with its reason. Newer mcp masks
    anything that isn't a ToolError as a bare 'Error executing tool'."""
    def deco(fn):
        @functools.wraps(fn)
        def run(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except ToolError:
                raise
            except Exception as e:
                raise ToolError(f"{type(e).__name__}: {e}") from e
        return mcp.tool(description=description)(run)
    return deco


@tool(
    description="Create a new spreadsheet in the user's My Drive root and return "
    "its id and url. Optionally name its tabs; otherwise it gets one 'Sheet1'. "
    "Cannot place it in a folder — the user moves it in Drive if they want."
)
def sheets_create(title: str, tab_names: list[str] | None = None) -> dict:
    return sheets.create(title, tab_names)


@tool(description="List tab names and sizes in a spreadsheet.")
def sheets_tabs(sheet_id: str) -> list[dict]:
    return sheets.tabs(sheet_id)


@tool(
    description="Read a tab. Returns rows as {row, values} with 1-indexed sheet "
    "row numbers. Optional a1 range (e.g. 'A1:H40') limits the read. "
    "formulas=True returns formula text instead of computed values — use it "
    "before editing a calculated sheet so you can see what you'd overwrite."
)
def sheets_read(sheet_id: str, tab: str, a1: str | None = None,
                formulas: bool = False) -> list[dict]:
    return sheets.read(sheet_id, tab, a1, formulas)


@tool(
    description="Batch-write cells. updates is a list of "
    "{tab, a1, value}, e.g. [{'tab':'Dashboard','a1':'B7','value':'done'}]. "
    "Write to a merged range's anchor cell to update it without unmerging."
)
def sheets_write(sheet_id: str, updates: list[dict]) -> dict:
    return sheets.write(sheet_id, updates)


@tool(
    description="Apply cell formatting without touching values. formats is a list of "
    "{tab, a1, format} where format is a Sheets API CellFormat, e.g. "
    "{'numberFormat':{'type':'CURRENCY','pattern':'₹#,##0.00'}} or "
    "{'textFormat':{'bold':true}} or {'backgroundColor':{'red':0.9,'green':0.9,'blue':0.9}}."
)
def sheets_format(sheet_id: str, formats: list[dict]) -> dict:
    return sheets.format_cells(sheet_id, formats)


@tool(
    description="Freeze header rows and/or leading columns so they stay visible "
    "while scrolling. Defaults to freezing the first row."
)
def sheets_freeze(sheet_id: str, tab: str, rows: int = 1, cols: int = 0) -> dict:
    return sheets.freeze(sheet_id, tab, rows, cols)


@tool(
    description="Add conditional-format rules — colour cells based on their contents. "
    "rules is a list of {tab, a1, condition, format}, where condition is a Sheets "
    "BooleanCondition, e.g. {'type':'NUMBER_LESS','values':[{'userEnteredValue':'0'}]} "
    "or {'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':'=$C2>$B2'}]}. "
    "Pass replace=true to clear existing rules on those tabs first — otherwise "
    "re-running stacks duplicates."
)
def sheets_conditional(sheet_id: str, rules: list[dict],
                       replace: bool = False) -> dict:
    return sheets.conditional(sheet_id, rules, replace)


@tool(description="Append rows below the last non-empty row of a tab.")
def sheets_append(sheet_id: str, tab: str, rows: list[list[str]]) -> dict:
    return sheets.append(sheet_id, tab, rows)


if __name__ == "__main__":
    mcp.run()
