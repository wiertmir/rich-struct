"""Lists, arrays, numpy arrays and pandas objects as rich tables.

Everything is duck-typed, so neither numpy nor pandas is imported (or required).
"""

from collections.abc import Mapping
from numbers import Integral, Real
from typing import Any, List, Optional, Tuple

from rich import box
from rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from rich.table import Table
from rich.text import Text

_MISSING = {"None", "nan", "NaN", "NaT", "<NA>"}
_GAP = "…"


def is_array(obj: Any) -> bool:
    """numpy arrays, pandas DataFrames/Series and anything else array-like with a shape."""
    return hasattr(obj, "__array__") and getattr(obj, "ndim", 0) > 0


def _clip(n: int, limit: int) -> List[Optional[int]]:
    """Positions to show out of ``n``: head and tail, with None marking the gap."""
    if n <= limit:
        return list(range(n))
    head = (limit + 1) // 2
    return [*range(head), None, *range(n - (limit - head), n)]


def _is_float(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, Integral) and not _is_bool(value)


def _is_bool(value: Any) -> bool:
    return type(value).__name__ in ("bool", "bool_")


def _cell(value: Any) -> Text:
    text = format(value, ".6g") if _is_float(value) else str(value)
    if isinstance(value, str):
        style = "repr.ellipsis" if value == _GAP else "repr.str"
    elif text in _MISSING:
        style = "repr.none"
    elif _is_bool(value):
        style = "repr.bool_true" if value else "repr.bool_false"
    else:
        style = "repr.number" if isinstance(value, Real) else "none"
    return Text(text, style=style)


def _column(values: List[Any]) -> List[Text]:
    """Cells of one column; its floats get the same number of decimals."""
    cells = [_cell(value) for value in values]
    floats = [i for i, value in enumerate(values) if _is_float(value) and value == value]
    if floats and not any("e" in cells[i].plain for i in floats):
        decimals = min(6, max(1, *(len(cells[i].plain.partition(".")[2]) for i in floats)))
        for i in floats:
            cells[i].plain = f"{values[i]:.{decimals}f}"
    return cells


class _Fitted:
    """Renders ``data`` with as many columns (up to ``max_cols``) as fit the console."""

    def __init__(
        self, data: Any, title: Optional[str], max_rows: int, max_cols: int, caption: bool = True
    ) -> None:
        self.data, self.title, self.max_rows, self.max_cols = data, title, max_rows, max_cols
        self.caption = caption

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        max_cols = self.max_cols
        unlimited = options.update_width(10_000)  # measure the table before rich squeezes it
        while True:
            table, caption = _build(self.data, self.max_rows, max_cols)
            if max_cols <= 2 or console.measure(table, options=unlimited).maximum <= options.max_width:
                break
            max_cols -= 1
        if self.title:
            yield Text(self.title, style="table.title")
        yield table
        if self.caption:
            yield Text(caption, style="table.caption")


def to_table(
    data: Any, *, title: Optional[str] = None, max_rows: int = 20, max_cols: int = 10
) -> RenderableType:
    """A renderable table for a list, array, numpy array, DataFrame or Series.

    Lists of dicts become records, lists of lists a grid, anything else one column.
    Long data shows its first and last rows/columns around a "…" gap, and columns
    that don't fit the console width are dropped into that gap too.
    """
    if is_array(data) and data.ndim > 2 and not hasattr(data, "iloc"):
        shown = min(len(data), 3)
        slices = [
            _Fitted(data[i], f"[{i}]", max_rows, max_cols, caption=False)
            if data.ndim == 3
            else to_table(data[i], title=f"[{i}]", max_rows=max_rows, max_cols=max_cols)
            for i in range(shown)
        ]
        if len(data) > shown:
            slices.append(Text(f"… {len(data) - shown} more", style="repr.ellipsis"))
        whole = f"{type(data).__name__} · shape {tuple(data.shape)} · dtype {data.dtype}"
        heading = [Text(title, style="table.title")] if title else []
        return Group(*heading, *slices, Text(whole, style="table.caption"))
    return _Fitted(data, title, max_rows, max_cols)


def _build(data: Any, max_rows: int, max_cols: int) -> Tuple[Table, str]:
    corner = ""
    if hasattr(data, "iloc"):  # pandas
        if data.ndim == 1:
            caption = f"Series · dtype {data.dtype} · {len(data)} items"
            data = data.to_frame(name="value" if data.name is None else data.name)
        else:
            caption = f"DataFrame · {data.shape[0]} rows × {data.shape[1]} columns"
        shown_rows, shown_cols = _clip(data.shape[0], max_rows), _clip(data.shape[1], max_cols)
        part = data.iloc[
            [i for i in shown_rows if i is not None], [j for j in shown_cols if j is not None]
        ]
        corner = "" if data.index.name is None else str(data.index.name)
        columns, index = list(part.columns), list(part.index)
        rows = [list(row) for row in part.itertuples(index=False, name=None)]
    elif is_array(data):  # numpy and friends
        caption = f"{type(data).__name__} · shape {tuple(data.shape)} · dtype {data.dtype}"
        grid = data.reshape(-1, 1) if data.ndim == 1 else data
        shown_rows, shown_cols = _clip(grid.shape[0], max_rows), _clip(grid.shape[1], max_cols)
        index = [i for i in shown_rows if i is not None]
        columns = [j for j in shown_cols if j is not None]
        rows = grid[index][:, columns].tolist()
        if data.ndim == 1:
            columns = ["value"]
    else:  # any other sequence: list, tuple, array.array, range, generator...
        kind = type(data).__name__
        data = list(data)
        caption = f"{kind} · {len(data)} items"
        shown_rows = _clip(len(data), max_rows)
        index = [i for i in shown_rows if i is not None]
        items = [data[i] for i in index]
        if items and all(isinstance(item, Mapping) for item in items):
            keys = list(dict.fromkeys(key for item in items for key in item))
            grid = [[item.get(key) for key in keys] for item in items]
        elif items and all(isinstance(item, (list, tuple)) for item in items):
            keys = list(range(max(map(len, items))))
            grid = [[*item, *[None] * (len(keys) - len(item))] for item in items]
        else:
            keys, grid = ["value"], [[item] for item in items]
        shown_cols = _clip(len(keys), max_cols)
        columns = [keys[j] for j in shown_cols if j is not None]
        rows = [[row[j] for j in shown_cols if j is not None] for row in grid]

    if None in shown_cols:
        gap = shown_cols.index(None)
        columns.insert(gap, _GAP)
        for row in rows:
            row.insert(gap, _GAP)
    if None in shown_rows:
        gap = shown_rows.index(None)
        index.insert(gap, _GAP)
        rows.insert(gap, [_GAP] * len(columns))

    cells = [_column([row[j] for row in rows]) for j in range(len(columns))]
    table = Table(box=box.ROUNDED, border_style="rule.line", header_style="table.header")
    table.add_column(corner, style="table.header", justify="right", no_wrap=True)
    for name, column in zip(columns, cells):
        numeric = all(cell.style in ("repr.number", "repr.none", "repr.ellipsis") for cell in column)
        table.add_column(str(name), justify="right" if numeric else "left")
    for label, *row in zip(index, *cells):
        table.add_row(str(label), *row)
    return table, caption
