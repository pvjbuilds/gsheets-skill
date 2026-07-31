"""MCP server exposing the sheets core to any Claude session. stdio transport."""

from mcp.server import MCPServer

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


@mcp.tool(
    description="Create a new spreadsheet in the user's My Drive root and return "
    "its id and url. Optionally name its tabs; otherwise it gets one 'Sheet1'. "
    "Cannot place it in a folder — the user moves it in Drive if they want."
)
def sheets_create(title: str, tab_names: list[str] | None = None) -> dict:
    return sheets.create(title, tab_names)


@mcp.tool(description="List tab names and sizes in a spreadsheet.")
def sheets_tabs(sheet_id: str) -> list[dict]:
    return sheets.tabs(sheet_id)


@mcp.tool(
    description="Read a tab. Returns rows as {row, values} with 1-indexed sheet "
    "row numbers. Optional a1 range (e.g. 'A1:H40') limits the read."
)
def sheets_read(sheet_id: str, tab: str, a1: str | None = None) -> list[dict]:
    return sheets.read(sheet_id, tab, a1)


@mcp.tool(
    description="Batch-write cells. updates is a list of "
    "{tab, a1, value}, e.g. [{'tab':'Dashboard','a1':'B7','value':'done'}]. "
    "Write to a merged range's anchor cell to update it without unmerging."
)
def sheets_write(sheet_id: str, updates: list[dict]) -> dict:
    return sheets.write(sheet_id, updates)


@mcp.tool(description="Append rows below the last non-empty row of a tab.")
def sheets_append(sheet_id: str, tab: str, rows: list[list[str]]) -> dict:
    return sheets.append(sheet_id, tab, rows)


if __name__ == "__main__":
    mcp.run()
