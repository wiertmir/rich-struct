import io
from array import array
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import get_args

import pytest
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

import rich_struct as rt
from rich_struct import ThemeName
from rich_struct.themes import _distance


def render(fn, *args, **kwargs) -> str:
    out = io.StringIO()
    fn(*args, file=out, **kwargs)
    return out.getvalue()


def test_theme_colours_reach_the_output(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    keyword = "38;2;187;154;247"  # Tokyo Night purple, #bb9af7
    assert keyword in render(rt.print_syntax, "def f(): pass", "python")
    assert keyword in render(rt.print_md, "```python\ndef f(): pass\n```")
    assert keyword not in render(rt.print_syntax, "def f(): pass", "python", theme="Nord")
    assert "38;2;122;162;247" in render(rt.print_json, {"a": 1})  # key, blue #7aa2f7


@dataclass
class Point:
    x: int
    y: str


MD = "## Printing structs\n\nSome `code` and:\n\n```python\nprint('hi')\n```\n"


def test_enum_has_12_dark_11_light_and_all_build():
    assert sum(t.is_dark for t in ThemeName) == 12
    assert ThemeName.DARK_MODERN.is_dark and not ThemeName.LIGHT_MODERN.is_dark
    assert ThemeName.WINTER_IS_COMING.is_dark and not ThemeName.GITHUB_LIGHT.is_dark
    assert sum(not t.is_dark for t in ThemeName) == 11
    assert rt.DEFAULT_THEME is ThemeName.TOKYO_NIGHT
    for t in ThemeName:
        assert isinstance(t.theme, Theme)
    assert get_args(rt.ThemeLiteral) == tuple(t.value for t in ThemeName)  # autocomplete list


@pytest.mark.parametrize("theme", [*ThemeName, "Dracula", Theme({"syntax.keyword": "red"})])
def test_every_printer_with_every_theme_kind(theme):
    assert "Printing structs" in render(rt.print, Markdown(MD), theme=theme)
    assert "Printing structs" in render(rt.print_md, MD, theme=theme)
    assert '"a": 1' in render(rt.print_json, {"a": 1}, theme=theme)
    assert '"a": 1' in render(rt.print_json, '{"a": 1}', theme=theme)
    assert "a: 1" in render(rt.print_yaml, "a: 1\n", theme=theme)
    assert "<a>" in render(rt.print_xml, "<a><b/></a>", theme=theme)
    assert "<b />" in render(rt.print_xml, ET.fromstring("<a><b/></a>"), theme=theme)
    assert "Point(" in render(rt.print_object, Point(1, "y"), theme=theme)
    assert "def" in render(rt.print_syntax, "def f(): pass", "python", theme=theme)


def test_every_printer_accepts_none(monkeypatch):
    helpers = [rt.print, rt.print_md, rt.print_yaml, rt.print_xml, rt.print_object, rt.print_table]
    for fn in helpers:
        assert render(fn, None) == "None\n", fn.__name__
    assert render(rt.print_syntax, None, "python") == "None\n"
    assert render(rt.print_table, None, title="t", max_rows=3) == "None\n"
    assert render(rt.print_json, None) == "null\n"
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    for fn in [*helpers, rt.print_json]:
        assert "3;38;2;187;154;247" in render(fn, None), fn.__name__  # italic Tokyo Night purple


def test_set_default_theme_changes_every_printer(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    tokyo_bg, nord_bg, dracula_bg = "48;2;26;27;38", "48;2;46;52;64", "48;2;40;42;54"
    printers = [rt.print, rt.print_md, rt.print_json, rt.print_yaml, rt.print_xml, rt.print_object, rt.print_table]
    try:
        rt.set_default_theme("Nord")
        for fn in printers:
            out = render(fn, "1")
            assert nord_bg in out and tokyo_bg not in out, fn.__name__
        assert dracula_bg in render(rt.print, "x", theme="Dracula")  # explicit theme still wins
        rt.set_default_theme(Theme({"background": "white on #010203"}))
        assert "48;2;1;2;3" in render(rt.print_md, "x")
        with pytest.raises(ValueError):
            rt.set_default_theme("Nope")
    finally:
        rt.set_default_theme()
    assert tokyo_bg in render(rt.print, "x")


def test_list_markers_stand_out_from_the_text():
    for t in ThemeName:
        styles = t.theme.styles
        hexes = {key: styles[key].color.get_truecolor().hex for key in
                 ("markdown.item.bullet", "markdown.item.number", "markdown.text", "markdown.strong")}
        assert hexes["markdown.item.bullet"] == hexes["markdown.item.number"]
        for other in ("markdown.text", "markdown.strong"):
            assert _distance(hexes["markdown.item.bullet"], hexes[other]) > 90, (t.value, other)


def test_plain_print_matches_builtin_semantics():
    assert render(rt.print, "a", "b", sep="-", end="!") == "a-b!"


def test_unknown_theme_name_raises():
    with pytest.raises(ValueError):
        rt.print("x", theme="Nope")


def test_background_fills_full_width(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.setenv("COLUMNS", "40")
    bg = "48;2;26;27;38"  # Tokyo Night #1a1b26
    table = Table("col")
    table.add_row("x")
    for args in [("hi",), ({"a": 1},), (Markdown(MD),), (table,), ("a", Markdown("b"), 3)]:
        out = render(rt.print, *args)
        assert out.strip(), args
        for line in Text.from_ansi(out).split():
            assert line.cell_len == 40, (args, line.plain)
            painted = sum(s.end - s.start for s in line.spans if s.style.bgcolor)
            assert painted == len(line), (args, line.plain)
        assert bg in out
    assert bg not in render(rt.print, "hi", background=False)
    assert bg not in render(rt.print, "hi", theme=Theme({"syntax.keyword": "red"}))


def test_tables_from_lists():
    out = render(rt.print_table, [{"a": 1, "b": "x"}, {"a": 2.5, "c": None}])
    assert all(word in out for word in ("a", "b", "c", "2.5", "None", "list · 2 items"))
    assert "array · 3 items" in render(rt.print_table, array("d", [1.0, 2.0, 0.1 + 0.2]))
    assert "0.30 " in render(rt.print_table, [0.1 + 0.2, 1.25])  # rounded, decimals aligned
    grid = render(rt.print_table, [[1, 2], [3]])
    assert "None" in grid  # ragged rows are padded
    assert "0 items" in render(rt.print_table, [])


def test_long_data_is_clipped_to_head_and_tail():
    out = render(rt.print_table, list(range(1000)), max_rows=4)
    labels = [line.split()[1] for line in out.splitlines() if line.startswith("│")]
    assert labels[1:] == ["0", "1", "…", "998", "999"]
    wide = render(rt.print_table, [list(range(50))], max_cols=4)
    assert "…" in wide and " 49 " in wide and " 25 " not in wide


def test_numpy_and_pandas_tables():
    np = pytest.importorskip("numpy")
    pd = pytest.importorskip("pandas")
    assert "shape (2, 3) · dtype int64" in render(rt.print_table, np.arange(6).reshape(2, 3))
    assert "shape (5,)" in render(rt.print_table, np.linspace(0, 1, 5))
    assert "[1]" in render(rt.print_table, np.zeros((2, 2, 2)))
    df = pd.DataFrame({"name": ["a", "b"], "x": [1.5, float("nan")], "ok": [True, False]})
    out = render(rt.print_table, df.set_index("name"))
    assert all(word in out for word in ("name", "x", "ok", "1.5", "nan", "True", "DataFrame · 2 rows × 2 columns"))
    assert "Series · dtype float64 · 2 items" in render(rt.print_table, df["x"])
    big = render(rt.print_table, pd.DataFrame(np.zeros((1000, 100))))
    assert "1000 rows × 100 columns" in big and len(big.splitlines()) < 30
    assert max(map(len, big.splitlines())) <= 80 and "0.0…" not in big  # columns dropped to fit
    # plain print() turns arrays and frames into tables too, but leaves lists alone
    assert "2 rows × 3 columns" in render(rt.print, df)
    assert "shape (2,)" in render(rt.print, np.array([1, 2]))
    assert render(rt.print, [1, 2]) == "[1, 2]\n"
