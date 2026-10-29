# rich-struct

[`rich`](https://github.com/Textualize/rich)'s `print`, with 25 themes (23 popular editor themes and two originals) and helpers for Markdown, HTML, JSON, YAML, XML, Python objects and tables (lists, numpy arrays, pandas DataFrames and Series), plus coloured [`structlog`](https://www.structlog.org) logging in the same themes.

> **Note:** rich-struct is not an official implementation or extension of `rich`, and it is not part of the [Textualize/rich](https://github.com/Textualize/rich) project or endorsed by it. It is an independent wrapper, a bridge that makes `rich` easier to use, especially in VS Code Jupyter notebooks.

```sh
pip install rich-struct          # add [yaml] to dump objects with print_yaml, [html] for print_html, [log] for rich_struct.log
```

```python
from rich.markdown import Markdown
from rich.theme import Theme
from rich_struct import ThemeName, print, print_md, print_json, print_yaml, print_xml, print_obj, print_syntax, print_table, print_list, print_html

print("[bold]hello[/bold]", {"a": 1})                 # drop-in rich.print, Midnight Slate by default
print(Markdown("## Printing structs"), theme=ThemeName.DRACULA)

print_md("# Title\n\n```python\nprint('hi')\n```")
print_json({"a": [1, 2, None]}, theme="Nord")         # enum value as a string works too
print_yaml("a: 1\nb: [x, y]")
print_xml("<a><b c='d'/></a>")
print_html("<h1>Title</h1><p>Some <b>bold</b> text</p>")  # rendered, not its tags
print_obj(my_dataclass, theme=ThemeName.GITHUB_LIGHT)
print_obj(data, max_list_length=10, max_string=80)    # long containers/strings end in "... +N"
print_obj(doc, apply_newlines=True)                   # "\n" in strings breaks the line instead
print_json(data, max_list_length=10)                  # same for JSON and YAML lists (print_yaml)
print_syntax("SELECT 1", "sql")                       # any pygments lexer
print_table(df, title="Sales")                        # DataFrame, Series, numpy array, list...
print(df)                                             # arrays and frames become tables in print too
print_err(ValueError("bad input"))                   # error text or exception, in the theme's error colour
print_list(series, head_tail_only=True)               # [1, 2.5, 'text',  ...  98, 99]: list, array, Series

print_md("# Mine", theme=Theme({"markdown.h1": "bold magenta", "syntax.keyword": "red"}))
```

Every function takes `theme=`: a `ThemeName`, its string value, or a rich `Theme`.
To change the theme for all of them at once, call `set_default_theme("Dracula")` (same accepted values; no argument resets to Midnight Slate).
Passing `None` to any of them prints `None` (JSON: `null`) in the theme's colour for null values instead of failing.

In VS Code notebooks rich shows output in its own monospace font (Menlo, DejaVu Sans Mono...). Call `use_rich_font_override(True)` to use the font plain `print()` gets instead; `False` switches back. Lines stay closer together than in `print()` output: VS Code gives `print()` a noticeably looser line height, while rich deliberately uses a tight `line-height:normal` so table and panel borders join into solid lines. Copying `print()`'s spacing would leave gaps in those borders.

`ThemeName.X.theme` gives you the underlying rich `Theme` to use with your own `Console`.

## Screenshots

One per kind of struct, each in a different theme. The [demo notebook](https://github.com/wiertmir/rich-struct/blob/main/demos.ipynb) shows every kind in all 25 themes; open it in Jupyter or VS Code to see the colours.

**Markdown** — `print_md`, Midnight Slate (the default)

![Markdown in the Midnight Slate theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/markdown.png)

**HTML** — `print_html`, Dracula

![HTML in the Dracula theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/html.png)

**JSON** — `print_json`, Nord

![JSON in the Nord theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/json.png)

**YAML** — `print_yaml`, One Dark Pro

![YAML in the One Dark Pro theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/yaml.png)

**XML** — `print_xml`, GitHub Dark

![XML in the GitHub Dark theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/xml.png)

**Python objects** — `print_obj`, Catppuccin Mocha

![Python objects in the Catppuccin Mocha theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/object.png)

**Code** — `print_syntax`, One Light

![Code in the One Light theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/code.png)

**Lists** — `print_table`, Catppuccin Latte

![Lists in the Catppuccin Latte theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/list.png)

**Sequences** — `print_list` with `head_tail_only`, Tokyo Night

![A sequence in the Tokyo Night theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/sequence.png)

**NumPy arrays** — `print_table`, Solarized Dark

![NumPy arrays in the Solarized Dark theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/numpy.png)

**pandas DataFrames** — `print_table`, GitHub Light

![pandas DataFrames in the GitHub Light theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/dataframe.png)

**pandas Series** — `print_table`, Night Owl

![pandas Series in the Night Owl theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/series.png)

## Tables

`print_table(data, title=None, max_rows=20, max_cols=10)` accepts:

- pandas `DataFrame` and `Series`, numpy arrays of any dimension (more than 2: one table per slice)
- lists of dicts (records), lists of lists (a grid), and any other sequence such as `array.array` or `range` (one column)

Numbers are right-aligned, floats in a column share their decimals, and missing values are dimmed.
Long data shows its head and tail around a `…` gap, and columns that don't fit the terminal width go into the gap as well.
`to_table(data)` returns the renderable instead of printing it. numpy and pandas are not dependencies.

## Lists

`print_list(data, wrap=True, head_tail_only=False, head_tail_size=100)` prints a list, tuple, `array.array`, numpy array or pandas `Series` as one sequence: `[123, 1444.555, 'Test text', 4345.666]`.

It wraps at the terminal width; `wrap=False` keeps it on one line.
`head_tail_only=True` shows only the first and last `head_tail_size` elements, with a highlighted `  ...  ` between them.

## Logging

`rich_struct.log` is coloured console logging (and, optionally, daily log files) on top of [`structlog`](https://www.structlog.org). It needs `pip install "rich-struct[log]"`; the rest of rich-struct doesn't.

```python
from rich_struct.log import get_logger

log = get_logger()                       # console only, nothing to set up
log.info("Processed %s in %03d ms.", position, elapsed)   # printf style...
log.info("Processed {} in {:03d} ms.", position, elapsed) # ...or str.format style
log.info("Saved", user="bob", retries=3)                  # fields: key=value
log.exception("Caught {!r}", err)                         # adds the traceback
```

```
12:33:30.238 INFO     Processed A-17 in 042 ms.
12:33:30.239 ERROR    Caught ZeroDivisionError('division by zero')
```

On the console the level name is coloured by level (error is the brightest red), and every argument by its type (text, numbers, `True`/`False`, `None`, paths, exceptions, anything else), using the theme's colours, never bold. A message that doesn't match its arguments is still logged, with the arguments appended; logging never raises.

`configure()` changes the defaults. It is optional, and call it before the first `get_logger()`:

```python
from rich_struct.log import configure

configure(level="info")                  # debug (default), info, warning, error or critical
configure(theme="Dracula")               # any rich-struct theme; default is the one from set_default_theme()
configure(message="tint")                # colour of the message text, see below
configure(console=False)                 # no console output
configure(file=True)                     # also write logs/<script name>_yyyy_mm_dd.log
configure(file="var/log", keep=14)       # another folder, keep 14 days
configure(handler=my_handler)            # any logging.Handler also gets every line
```

`message=` picks the colour of the message text: `"plain"` (default, the theme's text colour), `"level"` (the level's colour) or `"tint"` (the text colour with a hint of the level's). Fields keep their own colours either way.

`file=True` writes the same lines without colours, starting with the local date, time and UTC offset, and adding the logging `` `module.Class` `` (the class when the call is inside a method):

```
2026-10-29 12:33:30.238+09:00 INFO     `__main__.Job` Processed A-17 in 042 ms.
```

A new file starts at local midnight and only the newest `keep` (7) files stay. On free-threaded Python, both outputs also show the thread name, `[worker-1]`, after the level.

`configure()` is `structlog.configure()` underneath, so it applies to every structlog logger in the process. `examples/log_demo.py` in the repository shows it all.

## Themes

| Dark | Light |
|---|---|
| Tokyo Night | GitHub Light |
| Dracula | Solarized Light |
| One Dark Pro | One Light |
| Monokai | Catppuccin Latte |
| Nord | Gruvbox Light |
| Gruvbox Dark | Tokyo Night Light |
| Catppuccin Mocha | Ayu Light |
| Solarized Dark | Night Owl Light |
| GitHub Dark | Light+ |
| Night Owl | Everforest Light |
| Winter is Coming | Light Modern |
| Dark Modern | Paper Frost |
| Midnight Slate (default) | |

Themes are built from each theme's colour palette, not ported token-by-token from the editor.

Output is painted on the theme's background across the full width in Jupyter notebooks, and left on the terminal's own background in a console. Pass `background=True/False` to a call, or call `use_background(True/False)` once to change the default (`None` restores the automatic choice); nothing is painted or padded when the output has no colour (e.g. piped to a file). A custom `Theme` gets a background by defining a `background` style, e.g. `"background": "#c0caf5 on #1a1b26"`.

Code colours come from `syntax.*` styles (`text`, `comment`, `keyword`, `string`, `number`, `function`, `type`, `tag`, `attribute`, `operator`); a custom `Theme` may override any of them, and may set `syntax.block` (e.g. `"on #111c2e"`) to shade code blocks inside Markdown, and `repr.background` to give `print_obj` output its own background.
