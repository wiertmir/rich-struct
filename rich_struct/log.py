"""Coloured console logging on top of ``structlog``: ``log.info("Took {:03d} ms", ms)`` or ``log.info("Took %03d ms", ms)``."""

import colorsys
import re
import string
import sys
from numbers import Number
from pathlib import PurePath
from typing import Any, Dict, List, Optional, Tuple

import structlog
from rich.color import Color, ColorTriplet
from rich.default_styles import DEFAULT_STYLES
from rich.style import Style
from rich.text import Text
from rich.theme import Theme

import rich_struct
from . import print as _print
from . import ThemeName, ThemeType

__all__ = ["configure", "get_logger"]

# level -> theme style (the same styles print_obj uses); critical is also reversed
_LEVELS = {
    "debug": "repr.ellipsis",
    "info": "repr.call",
    "warning": "syntax.number",
    "error": "repr.error",
    "critical": "repr.error",
}
_NUMBERS = {name: no for no, name in enumerate(_LEVELS)}
_PERCENT = re.compile(r"%%|%[#0\- +]*\d*(?:\.\d+)?[hlL]?[diouxXeEfFgGcrsa]")


def _style(value: Any) -> str:
    if isinstance(value, bool):
        return f"repr.bool_{str(value).lower()}"
    if value is None:
        return "repr.none"
    if isinstance(value, Number):
        return "repr.number"
    if isinstance(value, str):
        return "repr.str"
    if isinstance(value, BaseException) or (isinstance(value, type) and issubclass(value, BaseException)):
        return "repr.exception"
    if isinstance(value, PurePath):
        return "repr.attrib_value"
    return "repr.path"


def _format(event: str, args: tuple, kwargs: Dict[str, Any]) -> List[Tuple[str, Optional[str]]]:
    """Split the message into ``(text, style)`` pieces; style is None for the message's own text and ``%%``."""
    pieces: List[Tuple[str, Optional[str]]] = []
    if args and _PERCENT.search(event):
        pos, n = 0, 0
        for m in _PERCENT.finditer(event):
            pieces.append((event[pos : m.start()], None))
            if m.group() == "%%":
                pieces.append(("%", None))
            else:
                pieces.append((m.group() % (args[n],), _style(args[n])))
                n += 1
            pos = m.end()
        pieces.append((event[pos:], None))
        if n != len(args):
            raise TypeError("not all arguments converted")
    elif "{" in event:
        fmt, auto = string.Formatter(), 0
        for literal, field, spec, conv in fmt.parse(event):
            pieces.append((literal, None))
            if field is not None:
                if field == "":
                    field, auto = str(auto), auto + 1
                value, _ = fmt.get_field(field, args, kwargs)
                text = fmt.format_field(fmt.convert_field(value, conv), spec)
                pieces.append((text, _style(value)))
    else:
        pieces.append((event, None))
    return pieces


class _Logger(structlog.BoundLoggerBase):
    """Keeps the arguments raw (structlog's own loggers would ``%``-format them before we can colour them)."""

    min_level = 0

    def _log(self, level: str, event: str, args: tuple, kw: Dict[str, Any]) -> None:
        if _NUMBERS[level] >= self.min_level:
            self._proxy_to_logger(level, event, positional_args=args, **kw)

    def debug(self, event: str, *args: Any, **kw: Any) -> None:
        self._log("debug", event, args, kw)

    def info(self, event: str, *args: Any, **kw: Any) -> None:
        self._log("info", event, args, kw)

    def warning(self, event: str, *args: Any, **kw: Any) -> None:
        self._log("warning", event, args, kw)

    def error(self, event: str, *args: Any, **kw: Any) -> None:
        self._log("error", event, args, kw)

    def critical(self, event: str, *args: Any, **kw: Any) -> None:
        self._log("critical", event, args, kw)

    def exception(self, event: str, *args: Any, **kw: Any) -> None:
        kw.setdefault("exc_info", True)
        self._log("error", event, args, kw)


def _blend(a: Style, b: Style, share: float) -> Style:
    """The colour of ``a`` moved ``share`` of the way to the colour of ``b``."""
    (r1, g1, b1), (r2, g2, b2) = (s.color.get_truecolor() for s in (a, b))
    mixed = ColorTriplet(*(round(x + (y - x) * share) for x, y in ((r1, r2), (g1, g2), (b1, b2))))
    return Style(color=Color.from_triplet(mixed))


def _brighten(style: Style) -> Style:
    """Full-brightness version of the colour, its hue pulled toward pure red (no pinkish tint)."""
    h, sat, _ = colorsys.rgb_to_hsv(*(c / 255 for c in style.color.get_truecolor()))
    rgb = colorsys.hsv_to_rgb((h if h < 0.5 else h - 1) * 0.3 % 1, sat, 1)
    return Style(color=Color.from_triplet(ColorTriplet(*(round(c * 255) for c in rgb))))


def _render(theme: Optional[ThemeType], message: str):
    def render(_logger: Any, method: str, event_dict: Dict[str, Any]) -> None:
        event_dict = dict(event_dict)
        event = str(event_dict.pop("event", ""))
        args = event_dict.pop("positional_args", ())
        stamp, level = event_dict.pop("timestamp", ""), event_dict.pop("level", method)
        exc = event_dict.pop("exception", "")
        try:
            pieces = _format(event, args, event_dict)
        except (TypeError, ValueError, LookupError, AttributeError):  # logging must not crash the program
            pieces = [(" ".join([event, *map(repr, args)]), None)]
        picked = rich_struct._default_theme if theme is None else theme
        styles = {**DEFAULT_STYLES, **(picked if isinstance(picked, Theme) else ThemeName(picked).theme).styles}

        def get(name: str) -> Style:  # the theme's style, minus bold
            return styles.get(name, styles["repr.error"]) + Style(bold=False)  # repr.exception: Midnight Slate only

        base = get(_LEVELS.get(level, "repr.ellipsis"))
        if level in ("error", "critical"):
            base = _brighten(base)
        body = {"plain": get("pretty"), "level": base, "tint": _blend(get("pretty"), base, 0.25)}[message]
        line = Text()
        line.append(f"{stamp[:-3]} ", get("repr.ellipsis"))
        line.append(f"{level.upper():<9}", base + Style(reverse=level == "critical"))
        for text, style in pieces:
            line.append(text, get(style) if style else body)
        for key, value in event_dict.items():
            line.append(f" {key}", get("repr.attrib_name"))
            line.append("=", get("repr.attrib_equal"))
            line.append(str(value), get(_style(value)))
        if exc:
            line.append("\n" + exc, base)
        _print(line, file=sys.stderr, theme=theme)
        raise structlog.DropEvent  # ponytail: printing here; the default logger would print a returned string itself

    return render


def configure(level: str = "debug", theme: Optional[ThemeType] = None, message: str = "plain") -> None:
    """Send ``structlog`` output to stderr, with arguments coloured by type and the level name by level.

    ``message`` colours the rest of the message: ``"plain"`` (the theme's text colour), ``"level"``
    (the level's colour) or ``"tint"`` (the text colour with a hint of the level's).

    Affects every structlog logger in the process (``structlog.configure`` is global).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S.%f", utc=False),
            structlog.processors.format_exc_info,
            _render(theme, message),
        ],
        wrapper_class=type("Logger", (_Logger,), {"min_level": _NUMBERS[level.lower()]}),
        cache_logger_on_first_use=True,
    )


_configured = False


def get_logger(*args: Any, **initial_values: Any) -> Any:
    """A structlog logger; the first call configures defaults (:func:`configure`) unless you did already."""
    global _configured
    if not _configured:
        _configured = True
        if not structlog.is_configured():
            configure()
    return structlog.get_logger(*args, **initial_values)
