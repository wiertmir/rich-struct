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


@pytest.fixture(autouse=True)
def paint_background():
    rt.use_background(True)  # most tests look at the painted output
    yield
    rt.use_background(None)  # back to auto


def render(fn, *args, **kwargs) -> str:
    out = io.StringIO()
    fn(*args, file=out, **kwargs)
    return out.getvalue()


def test_theme_colours_reach_the_output(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    keyword = "38;2;167;139;250"  # Midnight Slate violet, #a78bfa
    assert keyword in render(rt.print_syntax, "def f(): pass", "python")
    assert keyword in render(rt.print_md, "```python\ndef f(): pass\n```")
    assert keyword not in render(rt.print_syntax, "def f(): pass", "python", theme="Nord")
    assert "38;2;163;194;242" in render(rt.print_json, {"a": 1})  # key, #a3c2f2


@dataclass
class Point:
    x: int
    y: str


MD = "## Printing structs\n\nSome `code` and:\n\n```python\nprint('hi')\n```\n"


def test_enum_has_13_dark_12_light_and_all_build():
    assert sum(t.is_dark for t in ThemeName) == 13
    assert ThemeName.MIDNIGHT_SLATE.is_dark and not ThemeName.PAPER_FROST.is_dark
    assert ThemeName.DARK_MODERN.is_dark and not ThemeName.LIGHT_MODERN.is_dark
    assert ThemeName.WINTER_IS_COMING.is_dark and not ThemeName.GITHUB_LIGHT.is_dark
    assert sum(not t.is_dark for t in ThemeName) == 12
    assert rt.DEFAULT_THEME is ThemeName.MIDNIGHT_SLATE
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
    assert "Point(" in render(rt.print_obj, Point(1, "y"), theme=theme)
    assert "def" in render(rt.print_syntax, "def f(): pass", "python", theme=theme)


def test_every_printer_accepts_none(monkeypatch):
    helpers = [rt.print, rt.print_md, rt.print_yaml, rt.print_xml, rt.print_obj, rt.print_table]
    for fn in helpers:
        assert render(fn, None) == "None\n", fn.__name__
    assert render(rt.print_syntax, None, "python") == "None\n"
    assert render(rt.print_table, None, title="t", max_rows=3) == "None\n"
    assert render(rt.print_json, None) == "null\n"
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    for fn in helpers:
        assert "3;38;2;167;139;250" in render(fn, None), fn.__name__  # italic #a78bfa, same as JSON null
    assert "3;38;2;167;139;250" in render(rt.print_json, None)  # JSON null, italic #a78bfa


def test_set_default_theme_changes_every_printer(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    default_bg, nord_bg, dracula_bg = "48;2;11;19;32", "48;2;46;52;64", "48;2;40;42;54"
    printers = [rt.print, rt.print_md, rt.print_json, rt.print_yaml, rt.print_xml, rt.print_obj, rt.print_table]
    try:
        rt.set_default_theme("Nord")
        for fn in printers:
            out = render(fn, "1")
            assert nord_bg in out and default_bg not in out, fn.__name__
        assert dracula_bg in render(rt.print, "x", theme="Dracula")  # explicit theme still wins
        rt.set_default_theme(Theme({"background": "white on #010203"}))
        assert "48;2;1;2;3" in render(rt.print_md, "x")
        with pytest.raises(ValueError):
            rt.set_default_theme("Nope")
    finally:
        rt.set_default_theme()
    assert default_bg in render(rt.print, "x")


def test_list_markers_stand_out_from_the_text():
    for t in ThemeName:
        styles = t.theme.styles
        hexes = {key: styles[key].color.get_truecolor().hex for key in
                 ("markdown.item.bullet", "markdown.item.number", "markdown.text", "markdown.strong")}
        assert hexes["markdown.item.bullet"] == hexes["markdown.item.number"]
        for other in ("markdown.text", "markdown.strong"):
            assert _distance(hexes["markdown.item.bullet"], hexes[other]) > 90, (t.value, other)


def test_theme_specific_styles_and_markdown_code_block_background(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    block_bg, h1 = "48;2;17;28;46", "38;2;94;234;212"  # #111c2e, #5eead4
    out = render(rt.print_md, "# Title\n\n```python\nx = 1\n```", theme="Midnight Slate")
    assert block_bg in out and h1 in out
    assert block_bg not in render(rt.print_syntax, "x = 1", "python", theme="Midnight Slate")
    mine = Theme({"syntax.block": "on #010203"})  # custom themes can shade code blocks too
    assert "48;2;1;2;3" in render(rt.print_md, "```python\nx = 1\n```", theme=mine)


def test_objects_get_their_own_colours_and_background_in_midnight_slate(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    page_bg, object_bg = "48;2;11;19;32", "48;2;15;23;42"  # #0b1320, #0f172a
    out = render(rt.print_obj, Point(1, "y"))
    assert object_bg in out and page_bg not in out
    assert "38;2;163;194;242" in out and "1;38;2;121;192;255" in out  # property #a3c2f2 (as JSON keys), class bold #79c0ff (as GitHub Dark)
    assert object_bg not in render(rt.print_md, "text") and object_bg not in render(rt.print_obj, 1, background=False)
    assert "48;2;46;52;64" in render(rt.print_obj, 1, theme="Nord")  # other themes: the page background
    # dict keys take the property colour here, and stay string-coloured in themes without repr.key
    prop, slate_str, nord_str = "38;2;163;194;242", "38;2;163;230;53", "38;2;163;190;140"
    out = render(rt.print_obj, {"key": "value"})
    assert f"{prop};48;2;15;23;42m'key'" in out and f"{slate_str};48;2;15;23;42m'value'" in out
    assert f"{nord_str};48;2;46;52;64m'key'" in render(rt.print_obj, {"key": "value"}, theme="Nord")


def test_plain_print_matches_builtin_semantics():
    assert render(rt.print, "a", "b", sep="-", end="!") == "a-b!"


def test_unknown_theme_name_raises():
    with pytest.raises(ValueError):
        rt.print("x", theme="Nope")


def test_background_fills_full_width(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.setenv("COLUMNS", "40")
    bg = "48;2;11;19;32"  # Midnight Slate #0b1320
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


def test_print_list():
    assert render(rt.print_list, [123, 1444.555, "Test text", 4345.666]) == "[123, 1444.555, 'Test text', 4345.666]\n"
    assert render(rt.print_list, array("d", [1.0, 2.5])) == "[1.0, 2.5]\n"
    assert render(rt.print_list, None) == "None\n"
    long = list(range(60))
    assert len(render(rt.print_list, long).splitlines()) > 1
    assert render(rt.print_list, long, wrap=False) == f"{long}\n"
    assert render(rt.print_list, range(10), head_tail_only=True, head_tail_size=2) == "[0, 1  ...  8, 9]\n"
    assert render(rt.print_list, [1, 2, 3, 4], head_tail_only=True, head_tail_size=2) == "[1, 2, 3, 4]\n"
    with pytest.raises(ValueError):
        rt.print_list([1], head_tail_size=0)


def test_print_list_gap_is_highlighted(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    out = render(rt.print_list, list(range(10)), head_tail_only=True, head_tail_size=2)
    assert out.count("\x1b[1;7;") == 1 and "  ...  " in out  # only the gap is bold + reverse
    long = list(range(60))
    assert Text.from_ansi(render(rt.print_list, long, wrap=False)).plain.rstrip() == str(long)  # not cropped


def test_print_list_numpy_and_pandas():
    np = pytest.importorskip("numpy")
    pd = pytest.importorskip("pandas")
    assert render(rt.print_list, np.array([1.5, 2.0])) == "[1.5, 2.0]\n"
    assert render(rt.print_list, [np.float64(1.5), "a"]) == "[1.5, 'a']\n"
    series = pd.Series([10, 20, 30, 40, 50], index=[3, 4, 0, 1, 2])
    assert render(rt.print_list, series, head_tail_only=True, head_tail_size=1) == "[10  ...  50]\n"


def test_print_html_renders_instead_of_showing_tags(monkeypatch):
    pytest.importorskip("markdownify")
    html = """<html><head><title>T</title><style>p {color: red}</style></head><body>
    <!-- hidden --><script>alert(1)</script>
    <h1>Title</h1><p>Some <b>bold</b> and <a href="https://e.com">a link</a>.</p>
    <ul><li>one</li><li>two</li></ul>
    <pre><code class="language-python">def f(): pass</code></pre>
    <table><tr><th>name</th></tr><tr><td>Ada</td></tr></table></body></html>"""
    out = render(rt.print_html, html)
    for shown in ("Title", "Some bold and a link.", "• one", "def f(): pass", "name", "Ada"):
        assert shown in out
    for hidden in ("<", "color", "alert", "hidden", "**"):
        assert hidden not in out
    assert render(rt.print_html, None) == "None\n"
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    assert "38;2;167;139;250" in render(rt.print_html, html)  # the code block is highlighted as Python


def test_structs_stay_inline_among_other_arguments():
    @dataclass
    class S:
        a: int
        b: str

    assert render(rt.print, "ready:", True) == "ready: True\n"
    assert render(rt.print, "ready:", {"a": 1}, S(1, "x"), "!") == "ready: {'a': 1} S(a=1, b='x') !\n"
    assert render(rt.print, {"a": 1, "b": 2}, width=8).count("\n") > 1  # alone, it still expands as before


def test_long_lists_are_truncated():
    obj = render(rt.print_obj, {"a": list(range(50)), "s": "x" * 30}, max_list_length=3, max_string=5)
    assert "... +47" in obj and "'xxxxx'+25" in obj and "49" not in obj
    for data in ({"a": list(range(50))}, '{"a": [0, 1, 2, 3, 4]}'):
        out = render(rt.print_json, data, max_list_length=3)
        assert '"... +' in out and "4" not in out.replace("+47", "").replace("+2", "")
    assert render(rt.print_json, [1, 2], max_list_length=3) == render(rt.print_json, [1, 2])


def test_apply_newlines():
    data = {"text": "a\nb", "path": "C:\\new"}
    assert "'a\\nb'" in render(rt.print_obj, data)
    out = render(rt.print_obj, data, apply_newlines=True)
    assert "    'text': 'a\n             b'," in out and "'C:\\\\new'" in out
    out = render(rt.print_obj, ["a\r\nb\rc"], apply_newlines=True)
    assert "'a\n     b\n     c'" in out and "\\r" not in out


def test_long_yaml_lists_are_truncated():
    pytest.importorskip("yaml")
    for data in ({"a": list(range(50))}, "a: [0, 1, 2, 3, 4]"):
        out = render(rt.print_yaml, data, max_list_length=3)
        assert "... +" in out and "- 3" not in out
    assert render(rt.print_yaml, "a: 1  # kept as written") == "a: 1  # kept as written\n"


def test_rich_font_override_is_opt_in():
    import rich.jupyter

    original = rich.jupyter.JUPYTER_HTML_FORMAT
    assert "--notebook-cell-output-font-family" not in original
    try:
        rt.use_rich_font_override(True)
        assert "font-family:var(--notebook-cell-output-font-family,Menlo," in rich.jupyter.JUPYTER_HTML_FORMAT
        assert "monospace)" in rich.jupyter.JUPYTER_HTML_FORMAT
        rt.use_rich_font_override(False)
        assert rich.jupyter.JUPYTER_HTML_FORMAT == original
    finally:
        rt.use_rich_font_override(False)


def test_rich_font_override_paints_notebook_background(monkeypatch):
    import rich.console
    import rich.jupyter

    html = []
    monkeypatch.setattr(rich.console, "_is_jupyter", lambda: True)
    monkeypatch.setattr(rich.jupyter, "display", lambda segments, text: html.append(rich.jupyter._render_segments(segments)))
    try:
        rt.use_rich_font_override(True)
        rt.print_md("# Title")
        rt.print_md("# Title", background=False)
    finally:
        rt.use_rich_font_override(False)
    rt.print_md("# Title")
    assert '<pre style="background:#' in html[0]
    assert "background:" not in html[1].split(">")[0]
    assert "background:" not in html[2].split(">")[0]
    assert "--notebook-cell-output-font-family" not in rich.jupyter.JUPYTER_HTML_FORMAT


def test_print_md_keeps_h1_on_the_left():
    out = render(rt.print_md, "# Title", width=40, background=False)
    assert out.startswith("Title")


def test_background_default_follows_environment(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    bg = "48;2;11;19;32"
    rt.use_background(None)
    assert bg not in render(rt.print, "hi")  # terminal: off by default
    rt.use_background(True)
    assert bg in render(rt.print, "hi")
    assert bg not in render(rt.print, "hi", background=False)  # explicit argument wins
    rt.use_background(False)
    assert bg not in render(rt.print, "hi")
    assert bg in render(rt.print, "hi", background=True)


def test_print_err_shows_text_and_exceptions_in_error_style(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    red = "38;2;197;30;58"  # Midnight Slate repr.error red, #C51E3A
    assert "boom [x]" in render(rt.print_err, "boom [x]") and red in render(rt.print_err, "boom")
    assert "ValueError: bad" in render(rt.print_err, ValueError("bad"))
