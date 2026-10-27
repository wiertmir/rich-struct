"""Themed drop-in extension of ``rich.print``."""

import json
import re
import sys
import xml.etree.ElementTree as ET
from typing import IO, Any, Optional, Union

import rich.jupyter
from rich.console import Console, ConsoleOptions, RenderResult
from rich.highlighter import ReprHighlighter
from rich.json import JSON
from rich.markdown import Heading, Markdown
from rich.padding import Padding
from rich.pretty import Pretty, is_expandable, pretty_repr
from rich.protocol import is_renderable
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

from .tables import is_array, to_table
from .themes import DEFAULT_THEME, ThemeLiteral, ThemeName, syntax_theme

__all__ = [
    "DEFAULT_THEME",
    "ThemeLiteral",
    "ThemeName",
    "ThemeType",
    "print",
    "print_html",
    "print_json",
    "print_list",
    "print_err",
    "print_md",
    "print_obj",
    "print_syntax",
    "print_table",
    "print_xml",
    "print_yaml",
    "set_default_theme",
    "to_table",
    "use_background",
    "use_rich_font_override",
]

ThemeType = Union[ThemeName, Theme, ThemeLiteral]

_RICH_HTML_FORMAT = rich.jupyter.JUPYTER_HTML_FORMAT
_VSCODE_HTML_FORMAT = re.sub(
    r"font-family:([^\"]+)", r"font-family:var(--notebook-cell-output-font-family,\1)", _RICH_HTML_FORMAT, count=1
)


def use_rich_font_override(enabled: bool = True) -> None:
    """In VS Code notebooks, show output in the font plain ``print()`` uses instead of rich's Menlo/DejaVu list.

    Other Jupyter frontends keep rich's fonts either way. ``False`` goes back to rich's fonts everywhere.
    """
    global _font_override
    _font_override = enabled
    # ponytail: patches a rich module constant; pass our own HTML to IPython.display if rich renames it
    rich.jupyter.JUPYTER_HTML_FORMAT = _VSCODE_HTML_FORMAT if enabled else _RICH_HTML_FORMAT


_font_override = False


class _ObjectHighlighter(ReprHighlighter):
    """rich's repr highlighting, plus dict keys as ``repr.key`` (themes without it show them as strings)."""

    # ponytail: any quoted string followed by ": " counts as a key; a real parser if that misfires
    highlights = [*ReprHighlighter.highlights, r"""(?P<key>(?<!\w)(?:'[^'\n]*'|"[^"\n]*"))(?=: )"""]


# a quoted string in a repr; backslash escapes inside it don't end it
_STRING_LITERAL = re.compile(r"""(?<![\\\w])b?(['"])(?:\\.|(?!\1).)*\1""")


class _NewlineHighlighter(_ObjectHighlighter):
    """Object highlighting, then ``\\n``, ``\\r\\n`` and ``\\r`` in strings become indented line breaks."""

    def __call__(self, text: Union[str, Text]) -> Text:
        text = super().__call__(text)  # highlight first: string colours don't span line breaks
        plain = text.plain
        result = text.blank_copy()
        pos = 0
        for literal in _STRING_LITERAL.finditer(plain):
            pad = " " * (literal.start(1) - plain.rfind("\n", 0, literal.start()))
            for escape in re.finditer(r"\\r\\n|\\.", literal.group()):
                if escape.group() in ("\\n", "\\r\\n", "\\r"):
                    start = literal.start() + escape.start()
                    result.append_text(text[pos:start])
                    result.append("\n" + pad)
                    pos = literal.start() + escape.end()
        result.append_text(text[pos:])
        return result


_default_theme: ThemeType = DEFAULT_THEME
_paint: Optional[bool] = None  # None: paint in notebooks only


def use_background(paint: Optional[bool]) -> None:
    """Choose whether print functions paint the theme's background when called without ``background=``.

    Out of the box (and with ``None``) they paint in Jupyter notebooks and leave the terminal's own background alone.
    """
    global _paint
    _paint = paint


def set_default_theme(theme: ThemeType = DEFAULT_THEME) -> None:
    """Set the theme used by every print function called without ``theme=``.

    Call it with no argument to go back to Midnight Slate.
    """
    global _default_theme
    if not isinstance(theme, Theme):
        theme = ThemeName(theme)  # fail here, not at the next print
    _default_theme = theme


def print(
    *objects: Any,
    sep: str = " ",
    end: str = "\n",
    file: Optional[IO[str]] = None,
    theme: Optional[ThemeType] = None,
    background: Optional[bool] = None,
    **kwargs: Any,
) -> None:
    """``rich.print`` with a theme.

    ``theme`` is a :class:`ThemeName` (or its string value) or a rich ``Theme``;
    left out, it is the default theme (see :func:`set_default_theme`).
    ``Markdown`` and ``Syntax`` objects get their code colours from the theme too,
    and numpy arrays, pandas DataFrames and Series are shown as tables.
    The theme's background is painted across the full width when ``background=True``;
    left out, :func:`use_background` decides (by default: notebooks yes, terminals no).
    Nothing is painted when the output has no colour, e.g. when piped to a file.
    Extra keyword arguments go to ``Console.print`` (``style``, ``justify``, ...).

    Every ``print_*`` helper accepts None and prints it as ``None`` in the theme's
    ``repr.none`` style (``print_json`` prints JSON's ``null``, in the same colour).
    """
    if theme is None:
        theme = _default_theme
    rich_theme = theme if isinstance(theme, Theme) else ThemeName(theme).theme
    code_theme = syntax_theme(rich_theme)
    objects = tuple(to_table(obj) if is_array(obj) else obj for obj in objects)
    if len(objects) > 1:
        # rich puts dicts, dataclasses... on their own lines; keep them inline among other arguments
        objects = tuple(
            ReprHighlighter()(pretty_repr(obj, max_width=sys.maxsize)) if is_expandable(obj) else obj
            for obj in objects
        )
    for obj in objects:
        if isinstance(obj, Markdown):
            obj.code_theme = syntax_theme(rich_theme, block=True)
        elif isinstance(obj, Syntax):
            # ponytail: Syntax has no public theme setter; rebuild the object if rich renames this
            obj._theme = code_theme
    # width goes to the Console: Console.print can only narrow it, print_list needs it wider
    console = Console(theme=rich_theme, file=file, width=kwargs.pop("width", None))
    base = rich_theme.styles.get("background")
    if background is None:
        background = console.is_jupyter if _paint is None else _paint
    if background and base and console.color_system:
        if objects and all(isinstance(obj, Pretty) for obj in objects):
            # a theme may give objects their own background
            base += rich_theme.styles.get("repr.background", base)
        # fill whole lines: Padding expands renderables, justify pads plain text
        objects = tuple(
            Padding(obj, 0) if is_renderable(obj) and not isinstance(obj, (str, Text)) else obj
            for obj in objects
        )
        kwargs.setdefault("justify", "left")
        kwargs["style"] = base + console.get_style(kwargs.get("style") or "none")
    html_format = rich.jupyter.JUPYTER_HTML_FORMAT
    bgcolor = kwargs["style"].bgcolor if isinstance(kwargs.get("style"), Style) else None
    if _font_override and bgcolor:
        # the VS Code font is taller than its line box, so rows leave gaps; paint them in the theme background
        # ponytail: swaps a module global for one print; not thread-safe, fine for notebooks
        rich.jupyter.JUPYTER_HTML_FORMAT = html_format.replace(
            '<pre style="', f'<pre style="background:{bgcolor.get_truecolor().hex};', 1
        )
    try:
        console.print(*objects, sep=sep, end=end, **kwargs)
    finally:
        rich.jupyter.JUPYTER_HTML_FORMAT = html_format


def print_err(err: Union[str, BaseException], *, theme: Optional[ThemeType] = None, **kwargs: Any) -> None:
    """Print an error message, or an exception as ``TypeName: message``, in the theme's ``repr.error`` style."""
    msg = err if isinstance(err, str) else f"{type(err).__name__}: {err}"
    kwargs.setdefault("style", "repr.error")
    print(Text(msg), theme=theme, **kwargs)


def print_md(markdown: Optional[str], *, theme: Optional[ThemeType] = None, **kwargs: Any) -> None:
    if markdown is None:
        return print(None, theme=theme, **kwargs)
    print(_Markdown(markdown), theme=theme, **kwargs)


class _LeftHeading(Heading):
    """A heading kept on the left; rich centres ``#`` headings."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        text = self.text.copy()
        text.justify = "left"
        yield text


class _Markdown(Markdown):
    elements = {**Markdown.elements, "heading_open": _LeftHeading}


def _code_language(el: Any) -> str:
    """The language of a ``<pre>`` block, from a ``language-python`` style class on it or its ``<code>``."""
    classes = [c for tag in (el, el.find("code")) if tag for c in tag.get("class") or []]
    return next((c.partition("-")[2] for c in classes if c.startswith(("language-", "lang-"))), "")


def print_html(html: Optional[str], *, theme: Optional[ThemeType] = None, **kwargs: Any) -> None:
    """Print HTML rendered (headings, lists, tables, links...), not its tags (needs ``rich-struct[html]``).

    The page is converted to Markdown, so it gets the theme's Markdown styles;
    CSS, scripts and anything else Markdown has no word for are dropped.
    """
    if html is None:
        return print(None, theme=theme, **kwargs)
    from markdownify import markdownify

    # ponytail: regex drops what must not show as text; fine short of a <script> holding "</script>"
    html = re.sub(r"(?is)<(head|script|style|template)\b.*?</\1\s*>|<!--.*?-->", "", html)
    print_md(markdownify(html, heading_style="ATX", code_language_callback=_code_language), theme=theme, **kwargs)


def print_syntax(
    code: Optional[str], lexer: str, *, theme: Optional[ThemeType] = None, **kwargs: Any
) -> None:
    """Print ``code`` highlighted with any pygments ``lexer`` ("python", "toml", ...)."""
    if code is None:
        return print(None, theme=theme, **kwargs)
    print(Syntax(code, lexer, word_wrap=True), theme=theme, **kwargs)


def _truncate_lists(data: Any, max_list_length: int) -> Any:
    """``data`` with every list cut to ``max_list_length`` items, plus a ``"... +N"`` string for the rest."""
    if isinstance(data, dict):
        return {k: _truncate_lists(v, max_list_length) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        kept = [_truncate_lists(v, max_list_length) for v in data[:max_list_length]]
        # ponytail: the marker is a JSON string, so it is coloured like one; patch the rendered Text if that bothers
        return kept + [f"... +{len(data) - max_list_length}"] if len(data) > max_list_length else kept
    return data


def print_json(
    data: Any, *, max_list_length: Optional[int] = None, theme: Optional[ThemeType] = None, **kwargs: Any
) -> None:
    """Print a JSON string, or any JSON-serialisable object.

    With ``max_list_length``, lists longer than that show their first ``max_list_length``
    items and a ``"... +N"`` entry counting the rest.
    """
    if max_list_length is not None:
        data = _truncate_lists(json.loads(data) if isinstance(data, str) else data, max_list_length)
    rendered = JSON(data) if isinstance(data, str) else JSON.from_data(data, default=str)
    print(rendered, theme=theme, **kwargs)


def print_yaml(
    data: Any, *, max_list_length: Optional[int] = None, theme: Optional[ThemeType] = None, **kwargs: Any
) -> None:
    """Print a YAML string, or dump an object as YAML (needs ``rich-struct[yaml]``).

    With ``max_list_length``, lists longer than that show their first ``max_list_length``
    items and a ``... +N`` entry counting the rest (a string is parsed first).
    """
    if data is None:
        return print(None, theme=theme, **kwargs)
    if max_list_length is not None or not isinstance(data, str):
        import yaml

        if max_list_length is not None:
            data = _truncate_lists(yaml.safe_load(data) if isinstance(data, str) else data, max_list_length)
        data = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    print_syntax(data.rstrip("\n"), "yaml", theme=theme, **kwargs)


def print_xml(
    data: Union[str, ET.Element, ET.ElementTree, None],
    *,
    theme: Optional[ThemeType] = None,
    **kwargs: Any,
) -> None:
    """Print an XML string as-is, or an ElementTree element indented."""
    if data is None:
        return print(None, theme=theme, **kwargs)
    if not isinstance(data, str):
        root = data.getroot() if isinstance(data, ET.ElementTree) else data
        ET.indent(root)
        data = ET.tostring(root, encoding="unicode")
    print_syntax(data.rstrip("\n"), "xml", theme=theme, **kwargs)


def print_obj(
    obj: Any,
    *,
    max_list_length: Optional[int] = None,
    max_string: Optional[int] = None,
    apply_newlines: bool = False,
    theme: Optional[ThemeType] = None,
    **kwargs: Any,
) -> None:
    """Pretty-print any Python object (dataclasses, dicts, nested structures...).

    ``max_list_length`` cuts containers (lists, dicts, sets...) to that many items,
    followed by ``... +N``; ``max_string`` cuts long strings the same way.
    With ``apply_newlines``, ``\\n``, ``\\r\\n`` or ``\\r`` in strings starts a new line,
    indented under the opening quote.
    """
    if obj is None:
        return print(None, theme=theme, **kwargs)
    highlighter = _NewlineHighlighter() if apply_newlines else _ObjectHighlighter()
    pretty = Pretty(
        obj, expand_all=True, highlighter=highlighter, max_length=max_list_length, max_string=max_string
    )
    print(pretty, theme=theme, **kwargs)


def print_table(
    data: Any,
    *,
    title: Optional[str] = None,
    max_rows: int = 20,
    max_cols: int = 10,
    theme: Optional[ThemeType] = None,
    **kwargs: Any,
) -> None:
    """Print a list, array, numpy array, pandas DataFrame or Series as a table.

    Lists of dicts become records, lists of lists a grid. Data longer than
    ``max_rows``/``max_cols`` shows its head and tail around a "…" gap.
    """
    if data is None:
        return print(None, theme=theme, **kwargs)
    table = to_table(data, title=title, max_rows=max_rows, max_cols=max_cols)
    print(table, theme=theme, **kwargs)


def print_list(
    data: Any,
    *,
    wrap: bool = True,
    head_tail_only: bool = False,
    head_tail_size: int = 100,
    theme: Optional[ThemeType] = None,
    **kwargs: Any,
) -> None:
    """Print a list, array, numpy array or pandas Series as a sequence: ``[1, 2.5, 'text']``.

    Long sequences wrap at the terminal width unless ``wrap=False``. With
    ``head_tail_only``, only the first and last ``head_tail_size`` elements are
    shown, around a highlighted "  ...  " gap.
    """
    if data is None:
        return print(None, theme=theme, **kwargs)
    if head_tail_size < 1:
        raise ValueError("head_tail_size must be at least 1")
    if not (hasattr(data, "tolist") or isinstance(data, (list, tuple))):
        data = list(data)  # sets, generators...
    parts = [data]
    if head_tail_only and len(data) > 2 * head_tail_size:
        rows = getattr(data, "iloc", data)  # pandas slices by position only through iloc
        parts = [rows[:head_tail_size], rows[len(data) - head_tail_size :]]
    highlight = _ObjectHighlighter()
    text = Text().append("[", style="repr.brace")
    for i, part in enumerate(parts):
        if i:
            text.append("  ...  ", style="bold reverse")
        # tolist() turns numpy and pandas scalars into plain Python ones, also inside a plain list
        values = part.tolist() if hasattr(part, "tolist") else part
        values = (v.tolist() if hasattr(v, "tolist") else v for v in values)
        text.append_text(highlight(", ".join(map(repr, values))))
    text.append("]", style="repr.brace")
    if not wrap:
        # one line however long: the terminal, not rich, decides what to do with it
        kwargs["width"] = max(text.cell_len, Console(file=kwargs.get("file")).width)
    print(text, theme=theme, **kwargs)
