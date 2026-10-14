"""Themed drop-in extension of ``rich.print``."""

import re
import sys
import xml.etree.ElementTree as ET
from typing import IO, Any, Optional, Union

from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.json import JSON
from rich.markdown import Markdown
from rich.padding import Padding
from rich.pretty import Pretty, is_expandable, pretty_repr
from rich.protocol import is_renderable
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
    "print_md",
    "print_obj",
    "print_syntax",
    "print_table",
    "print_xml",
    "print_yaml",
    "set_default_theme",
    "to_table",
]

ThemeType = Union[ThemeName, Theme, ThemeLiteral]


class _ObjectHighlighter(ReprHighlighter):
    """rich's repr highlighting, plus dict keys as ``repr.key`` (themes without it show them as strings)."""

    # ponytail: any quoted string followed by ": " counts as a key; a real parser if that misfires
    highlights = [*ReprHighlighter.highlights, r"""(?P<key>(?<!\w)(?:'[^'\n]*'|"[^"\n]*"))(?=: )"""]

_default_theme: ThemeType = DEFAULT_THEME


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
    background: bool = True,
    **kwargs: Any,
) -> None:
    """``rich.print`` with a theme.

    ``theme`` is a :class:`ThemeName` (or its string value) or a rich ``Theme``;
    left out, it is the default theme (see :func:`set_default_theme`).
    ``Markdown`` and ``Syntax`` objects get their code colours from the theme too,
    and numpy arrays, pandas DataFrames and Series are shown as tables.
    The theme's background is painted across the full terminal width unless
    ``background=False`` (or the output has no colour, e.g. when piped to a file).
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
    console.print(*objects, sep=sep, end=end, **kwargs)


def print_md(markdown: Optional[str], *, theme: Optional[ThemeType] = None, **kwargs: Any) -> None:
    if markdown is None:
        return print(None, theme=theme, **kwargs)
    print(Markdown(markdown), theme=theme, **kwargs)


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


def print_json(data: Any, *, theme: Optional[ThemeType] = None, **kwargs: Any) -> None:
    """Print a JSON string, or any JSON-serialisable object."""
    json = JSON(data) if isinstance(data, str) else JSON.from_data(data, default=str)
    print(json, theme=theme, **kwargs)


def print_yaml(data: Any, *, theme: Optional[ThemeType] = None, **kwargs: Any) -> None:
    """Print a YAML string, or dump an object as YAML (needs ``rich-struct[yaml]``)."""
    if data is None:
        return print(None, theme=theme, **kwargs)
    if not isinstance(data, str):
        import yaml

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


def print_obj(obj: Any, *, theme: Optional[ThemeType] = None, **kwargs: Any) -> None:
    """Pretty-print any Python object (dataclasses, dicts, nested structures...)."""
    if obj is None:
        return print(None, theme=theme, **kwargs)
    print(Pretty(obj, expand_all=True, highlighter=_ObjectHighlighter()), theme=theme, **kwargs)


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
