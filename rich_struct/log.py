"""Coloured console logging on top of ``structlog``: ``log.info("Took {:03d} ms", ms)`` or ``log.info("Took %03d ms", ms)``."""

import colorsys
import io
import logging
import os
import re
import string
import sys
import threading
from datetime import date, datetime
from numbers import Number
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional, Tuple, Union

import rich.jupyter
import structlog
from rich.color import Color, ColorTriplet
from rich.console import Console
from rich.default_styles import DEFAULT_STYLES
from rich.style import Style
from rich.text import Text
from rich.theme import Theme

import rich_struct
from . import print as _print
from . import ThemeName, ThemeType, _blend, _frame

__all__ = ["DailyFileHandler", "Logger", "configure", "get_logger"]

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


def _when(value: datetime) -> str:
    """Date, time to the millisecond and the datetime's own UTC offset (none if naive)."""
    return value.isoformat(sep=" ", timespec="milliseconds")


def _str(value: Any) -> str:
    return _when(value) if isinstance(value, datetime) else str(value)


def _format(event: str, args: tuple, kwargs: Dict[str, Any]) -> List[Tuple[str, Optional[str]]]:
    """Split the message into ``(text, style)`` pieces; style is None for the message's own text and ``%%``."""
    pieces: List[Tuple[str, Optional[str]]] = []
    if args and _PERCENT.search(event):
        pos, n = 0, 0
        for m in _PERCENT.finditer(event):
            pieces.append((event[pos : m.start()], None))
            if m.group() == "%%":
                pieces.append(("%", None))
            elif m.group() == "%s":
                pieces.append((_str(args[n]), _style(args[n])))
                n += 1
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
                text = _str(value) if not spec and not conv else fmt.format_field(fmt.convert_field(value, conv), spec)
                pieces.append((text, _style(value)))
    else:
        pieces.append((event, None))
    return pieces


class Logger(structlog.BoundLoggerBase):
    """What :func:`get_logger` returns. ``event`` is a ``%`` or ``{}`` format string for ``*args``;
    ``**kw`` become ``key=value`` fields. Binding, contextvars and the rest come from ``structlog``'s ``BoundLoggerBase``."""

    min_level = 0

    def _log(self, level: str, event: str, args: tuple, kw: Dict[str, Any]) -> None:
        if _NUMBERS[level] >= self.min_level:
            self._proxy_to_logger(level, event, positional_args=args, _site=_site(sys._getframe(2)), **kw)

    def debug(self, event: str, *args: Any, **kw: Any) -> None:
        """Log at DEBUG level."""
        self._log("debug", event, args, kw)

    def info(self, event: str, *args: Any, **kw: Any) -> None:
        """Log at INFO level."""
        self._log("info", event, args, kw)

    def warning(self, event: str, *args: Any, **kw: Any) -> None:
        """Log at WARNING level."""
        self._log("warning", event, args, kw)

    def error(self, event: str, *args: Any, **kw: Any) -> None:
        """Log at ERROR level."""
        self._log("error", event, args, kw)

    def critical(self, event: str, *args: Any, **kw: Any) -> None:
        """Log at CRITICAL level."""
        self._log("critical", event, args, kw)

    def exception(self, event: str, *args: Any, **kw: Any) -> None:
        """Like ``error``, with the exception being handled and its traceback."""
        kw.setdefault("exc_info", True)
        self._log("error", event, args, kw)

    # the same as structlog's, only typed to give back a Logger
    def bind(self, **new_values: Any) -> "Logger":
        """A copy of this logger with ``new_values`` added to every line as fields."""
        return super().bind(**new_values)  # type: ignore[return-value]

    def new(self, **new_values: Any) -> "Logger":
        """A copy with the bound fields replaced by ``new_values``."""
        return super().new(**new_values)  # type: ignore[return-value]

    def unbind(self, *keys: str) -> "Logger":
        """A copy without the bound fields ``keys``."""
        return super().unbind(*keys)  # type: ignore[return-value]


def _site(frame: Any) -> str:
    """``module`` or ``module.Class`` of the code that logged (the class of its ``self`` / ``cls`` argument)."""
    code = frame.f_code
    first = frame.f_locals.get(code.co_varnames[0]) if code.co_argcount and code.co_varnames[0] in ("self", "cls") else None
    cls = first if isinstance(first, type) else type(first)
    return frame.f_globals.get("__name__", "?") + (f".{cls.__name__}" if first is not None else "")


def _free_threaded() -> bool:
    return not getattr(sys, "_is_gil_enabled", lambda: True)()


def _brighten(style: Style) -> Style:
    """Full-brightness version of the colour, its hue pulled toward pure red (no pinkish tint)."""
    h, sat, _ = colorsys.rgb_to_hsv(*(c / 255 for c in style.color.get_truecolor()))
    rgb = colorsys.hsv_to_rgb((h if h < 0.5 else h - 1) * 0.3 % 1, sat, 1)
    return Style(color=Color.from_triplet(ColorTriplet(*(round(c * 255) for c in rgb))))


class DailyFileHandler(logging.FileHandler):
    """Writes to ``<folder>/<name>_yyyy_mm_dd.log``: a new file on the first line logged after local midnight,
    and only the newest ``keep`` files (days) are left."""

    def __init__(self, folder: Union[str, "os.PathLike[str]"], name: str, keep: int = 7):
        self.folder, self.prefix, self.keep = Path(folder), name, keep
        self.folder.mkdir(parents=True, exist_ok=True)
        super().__init__(self._path(), encoding="utf-8")
        self._prune()

    def _path(self) -> str:
        return os.path.abspath(self.folder / f"{self.prefix}_{date.today():%Y_%m_%d}.log")

    def _prune(self) -> None:
        for old in sorted(self.folder.glob(f"{self.prefix}_*.log"))[: -self.keep]:
            old.unlink()

    def emit(self, record: logging.LogRecord) -> None:
        if (path := self._path()) != self.baseFilename:  # the day changed
            if self.stream:
                self.stream.close()
                self.stream = None  # FileHandler.emit reopens it, at the new path
            self.baseFilename = path
            super().emit(record)
            self._prune()  # after emitting, so the new file counts
        else:
            super().emit(record)


def _in_notebook() -> bool:
    return Console().is_jupyter


_block: Dict[str, Any] = {"mark": None, "handle": None, "html": [], "text": []}
_block_lock = threading.Lock()


def _kernel_mark() -> Any:
    """Changes whenever the kernel sends anything (a print, a plot, a new cell); prints still buffered are sent first."""
    from IPython import get_ipython

    shell = get_ipython()
    session = getattr(getattr(shell, "kernel", None), "session", None)
    sys.stdout.flush()
    sys.stderr.flush()
    # ponytail: any message counts, so a VS Code variable refresh during an await also starts a new block
    return getattr(session, "message_count", None), getattr(shell, "execution_count", None)


def _show_in_notebook(line: Text, background: Optional[Style], accent: Style) -> None:
    """Lines logged one after another go into one block, updated in place (a display per line leaves gaps);
    anything else the cell outputs in between ends the block, so the next line starts a new one."""
    from IPython.display import display

    out = Console(record=True, file=io.StringIO(), width=10_000, color_system="truecolor", force_jupyter=False)
    out.print(line, soft_wrap=True)
    html = out.export_html(inline_styles=True, code_format="{code}")
    box = _frame(background)
    if accent.color:
        box += f";border-left:3px solid {accent.color.get_truecolor().hex}"
    # rich's <pre> (and its font, see use_rich_font_override), our block style last so it wins
    block = rich.jupyter.JUPYTER_HTML_FORMAT.replace(
        '">{code}', f';white-space:pre-wrap;margin:0;padding:6px 10px;border-radius:4px;{box}">{{code}}', 1
    )
    with _block_lock:
        if _block["handle"] is None or _kernel_mark() != _block["mark"]:
            _block.update(handle=None, html=[], text=[])
        _block["html"].append(html)
        _block["text"].append(line.plain)
        # ponytail: re-sends the whole block per line, O(n^2) for thousands of lines in a row
        bundle = {"text/html": block.format(code="".join(_block["html"]).rstrip("\n")), "text/plain": "\n".join(_block["text"])}
        if _block["handle"] is None:
            _block["handle"] = display(bundle, raw=True, display_id=True)
        else:
            _block["handle"].update(bundle, raw=True)
        _block["mark"] = _kernel_mark()


def _render(theme: Optional[ThemeType], message: str, console: bool, thread: bool, handlers: List[logging.Handler]):
    notebook = console and _in_notebook()

    def render(_logger: Any, method: str, event_dict: Dict[str, Any]) -> None:
        event_dict = dict(event_dict)
        event = str(event_dict.pop("event", ""))
        args = event_dict.pop("positional_args", ())
        stamp, level = event_dict.pop("timestamp", ""), event_dict.pop("level", method)
        exc = event_dict.pop("exception", "")
        site = event_dict.pop("_site", "")
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
        if thread:
            line.append(f"[{threading.current_thread().name}] ", get("repr.ellipsis"))
        cut = len(line)
        for text, style in pieces:
            line.append(text, get(style) if style else body)
        for key, value in event_dict.items():
            line.append(f" {key}", get("repr.attrib_name"))
            line.append("=", get("repr.attrib_equal"))
            line.append(_str(value), get(_style(value)))
        if exc:
            line.append("\n" + exc, base)
        if console:
            if notebook:
                _show_in_notebook(line, styles.get("background"), get("repr.call"))
            else:
                _print(line, file=sys.stderr, theme=theme)
        if handlers:  # same line without colours, dated with local time and UTC offset
            when = _when(datetime.now().astimezone())
            shown = len(stamp) - 3 + 1  # stamp is HH:MM:SS.ffffff; the line shows HH:MM:SS.fff and a space
            plain = f"{when} {line.plain[shown:cut]}`{site}` {line.plain[cut:]}"
            record = logging.makeLogRecord({"msg": plain, "levelno": _NUMBERS[level] * 10 or 10})
            for handler in handlers:
                handler.handle(record)
        raise structlog.DropEvent  # ponytail: printing here; the default logger would print a returned string itself

    return render


def configure(
    level: str = "debug",
    theme: Optional[ThemeType] = None,
    message: str = "plain",
    *,
    console: bool = True,
    thread: Optional[bool] = None,
    file: Union[bool, str, "os.PathLike[str]"] = False,
    keep: int = 7,
    handler: Optional[logging.Handler] = None,
) -> None:
    """Set up ``structlog``: arguments coloured by type and the level name by level, on stderr.

    ``message`` colours the rest of the message: ``"plain"`` (the theme's text colour), ``"level"``
    (the level's colour) or ``"tint"`` (the text colour with a hint of the level's).
    ``console=False`` turns the console output off.
    ``thread`` puts the thread name, ``[MainThread]``, in the lines; by default only on free-threaded Python,
    where threads really run in parallel.
    ``file=True`` also writes uncoloured lines to ``logs/<script name>_yyyy_mm_dd.log``, with local time and UTC offset,
    thread name (if ``thread``) and ``module.Class``; a new file every local midnight, the last ``keep``
    days kept. Give a folder instead of ``True`` to write elsewhere.
    ``handler`` is any other ``logging.Handler`` that should get the same lines.

    Affects every structlog logger in the process (``structlog.configure`` is global).
    """
    handlers = [handler] if handler else []
    if file:
        script = getattr(sys.modules["__main__"], "__file__", None)
        handlers.append(DailyFileHandler("logs" if file is True else file, Path(script).stem if script else "app", keep))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S.%f", utc=False),
            structlog.processors.format_exc_info,
            _render(theme, message, console, _free_threaded() if thread is None else thread, handlers),
        ],
        wrapper_class=type("ConfiguredLogger", (Logger,), {"min_level": _NUMBERS[level.lower()]}),
        cache_logger_on_first_use=True,
    )


_configured = False


def get_logger(*args: Any, **initial_values: Any) -> Logger:
    """A :class:`Logger`; the first call configures defaults (:func:`configure`) unless you did already.

    ``initial_values`` are bound to it as fields. (It is structlog's lazy proxy underneath,
    so any other attribute reaches structlog's own logger.)
    """
    global _configured
    if not _configured:
        _configured = True
        if not structlog.is_configured():
            configure()
    return structlog.get_logger(*args, **initial_values)  # type: ignore[no-any-return]
