"""Self-check for the bits that can break silently: row numbering, tab grouping,
unknown-tab rejection. Run: .venv/bin/python test_sheets.py  (no network, no auth)"""

import sheets


class FakeWS:
    def __init__(self, title, grid):
        self.title, self.grid = title, grid
        self.batches, self.appended, self.formats = [], [], []
        self.row_count, self.col_count = len(grid), 8

    def get_values(self, value_render_option=None):
        return self.grid

    def get(self, a1, value_render_option=None):
        lo = int("".join(c for c in a1.split(":")[0] if c.isdigit()))
        hi = int("".join(c for c in a1.split(":")[1] if c.isdigit()))
        return self.grid[lo - 1 : hi]

    def batch_update(self, batch, value_input_option=None):
        self.batches.append(batch)

    def batch_format(self, batch):
        self.formats.append(batch)

    def append_rows(self, rows, value_input_option=None):
        self.appended.extend(rows)


class FakeSheet:
    def __init__(self, ws):
        self.ws = {w.title: w for w in ws}

    def worksheets(self):
        return list(self.ws.values())

    def worksheet(self, t):
        return self.ws[t]


def fake(sheet):
    sheets._client = type("C", (), {"open_by_key": staticmethod(lambda _id: sheet)})()


def demo():
    dash = FakeWS("Dashboard", [["SECTION", ""], ["Item one", "old value"]])
    log = FakeWS("Log", [["Name", "Status"], ["Project A", "Pending"]])
    fake(FakeSheet([dash, log]))

    # read: 1-indexed row numbers, and offset preserved for ranged reads
    assert sheets.read("id", "Dashboard")[1] == {"row": 2, "values": ["Item one", "old value"]}
    assert sheets.read("id", "Dashboard", "A2:B2")[0]["row"] == 2

    # write: grouped into one batch call per tab, not one per cell
    r = sheets.write("id", [
        {"tab": "Dashboard", "a1": "B2", "value": "new value"},
        {"tab": "Dashboard", "a1": "B3", "value": "another"},
        {"tab": "Log", "a1": "B2", "value": "Approved"},
    ])
    assert r == {"cells_written": 3, "tabs": ["Dashboard", "Log"]}
    assert len(dash.batches) == 1 and len(dash.batches[0]) == 2, dash.batches
    assert dash.batches[0][0] == {"range": "B2", "values": [["new value"]]}
    assert len(log.batches) == 1

    # unknown tab rejected before ANY write lands (typo must not half-apply)
    dash.batches.clear()
    try:
        sheets.write("id", [{"tab": "Dashboard", "a1": "B2", "value": "x"},
                            {"tab": "Dashbaord", "a1": "B2", "value": "x"}])
        raise SystemExit("FAIL: bad tab accepted")
    except ValueError:
        pass
    assert dash.batches == [], "partial write leaked before validation"

    assert sheets.append("id", "Log", [["Project B", "New"]])["rows_appended"] == 1
    assert log.appended == [["Project B", "New"]]

    # format: same grouping + validation path as write, and values stay untouched
    bold = {"textFormat": {"bold": True}}
    money = {"numberFormat": {"type": "CURRENCY", "pattern": "#,##0.00"}}
    r = sheets.format_cells("id", [
        {"tab": "Log", "a1": "A1:B1", "format": bold},
        {"tab": "Log", "a1": "B2:B99", "format": money},
    ])
    assert r == {"ranges_formatted": 2, "tabs": ["Log"]}
    assert len(log.formats) == 1 and len(log.formats[0]) == 2, log.formats
    assert log.formats[0][0] == {"range": "A1:B1", "format": bold}
    assert log.grid[1] == ["Project A", "Pending"], "formatting must not alter values"

    log.formats.clear()
    try:
        sheets.format_cells("id", [{"tab": "Lgo", "a1": "A1", "format": bold}])
        raise SystemExit("FAIL: bad tab accepted")
    except ValueError:
        pass
    assert log.formats == [], "partial format leaked before validation"
    print("ok")


if __name__ == "__main__":
    demo()
