"""Themed drop-in extension of ``rich.print``."""

import xml.etree.ElementTree as ET
from typing import IO, Any, Optional, Union

from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.json import JSON
from rich.markdown import Markdown
from rich.padding import Padding
from rich.pretty import Pretty
from rich.protocol import is_renderable
from rich.syntax import Syntax
from rich.theme import Theme

from .tables import is_array, to_table
from .themes import DEFAULT_THEME, ThemeLiteral, ThemeName, syntax_theme

__all__ = [
    "DEFAULT_THEME",
    "ThemeLiteral",
    "ThemeName",
    "ThemeType",
    "print",
    "print_json",
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
    for obj in objects:
        if isinstance(obj, Markdown):
            obj.code_theme = syntax_theme(rich_theme, block=True)
        elif isinstance(obj, Syntax):
            # ponytail: Syntax has no public theme setter; rebuild the object if rich renames this
            obj._theme = code_theme
    console = Console(theme=rich_theme, file=file)
    base = rich_theme.styles.get("background")
    if background and base and console.color_system:
        if objects and all(isinstance(obj, Pretty) for obj in objects):
            # a theme may give objects their own background
            base += rich_theme.styles.get("repr.background", base)
        # fill whole lines: Padding expands renderables, justify pads plain text
        objects = tuple(
            Padding(obj, 0) if is_renderable(obj) and not isinstance(obj, str) else obj
            for obj in objects
        )
        kwargs.setdefault("justify", "left")
        kwargs["style"] = base + console.get_style(kwargs.get("style") or "none")
    console.print(*objects, sep=sep, end=end, **kwargs)


def print_md(markdown: Optional[str], *, theme: Optional[ThemeType] = None, **kwargs: Any) -> None:
    if markdown is None:
        return print(None, theme=theme, **kwargs)
    print(Markdown(markdown), theme=theme, **kwargs)


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
