# rich-struct

[`rich`](https://github.com/Textualize/rich)'s `print`, with 25 themes (23 popular editor themes and two originals) and helpers for Markdown, JSON, YAML, XML, Python objects and tables (lists, numpy arrays, pandas DataFrames and Series).

```sh
pip install rich-struct          # add [yaml] to dump objects with print_yaml
```

```python
from rich.markdown import Markdown
from rich.theme import Theme
from rich_struct import ThemeName, print, print_md, print_json, print_yaml, print_xml, print_obj, print_syntax, print_table

print("[bold]hello[/bold]", {"a": 1})                 # drop-in rich.print, Midnight Slate by default
print(Markdown("## Printing structs"), theme=ThemeName.DRACULA)

print_md("# Title\n\n```python\nprint('hi')\n```")
print_json({"a": [1, 2, None]}, theme="Nord")         # enum value as a string works too
print_yaml("a: 1\nb: [x, y]")
print_xml("<a><b c='d'/></a>")
print_obj(my_dataclass, theme=ThemeName.GITHUB_LIGHT)
print_syntax("SELECT 1", "sql")                       # any pygments lexer
print_table(df, title="Sales")                        # DataFrame, Series, numpy array, list...
print(df)                                             # arrays and frames become tables in print too

print_md("# Mine", theme=Theme({"markdown.h1": "bold magenta", "syntax.keyword": "red"}))
```

Every function takes `theme=`: a `ThemeName`, its string value, or a rich `Theme`.
To change the theme for all of them at once, call `set_default_theme("Dracula")` (same accepted values; no argument resets to Midnight Slate).
Passing `None` to any of them prints `None` (JSON: `null`) in the theme's colour for null values instead of failing.
`ThemeName.X.theme` gives you the underlying rich `Theme` to use with your own `Console`.

## Screenshots

One per kind of struct, each in a different theme. The [demo notebook](https://github.com/wiertmir/rich-struct/blob/main/demos.ipynb) shows every kind in all 25 themes; open it in Jupyter or VS Code to see the colours.

**Markdown** — `print_md`, Midnight Slate (the default)

![Markdown in the Midnight Slate theme](https://raw.githubusercontent.com/wiertmir/rich-struct/main/screenshots/markdown.png)

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

Output is painted on the theme's background across the full terminal width. Pass `background=False` to keep the terminal's own background; nothing is painted or padded when the output has no colour (e.g. piped to a file). A custom `Theme` gets a background by defining a `background` style, e.g. `"background": "#c0caf5 on #1a1b26"`.

Code colours come from `syntax.*` styles (`text`, `comment`, `keyword`, `string`, `number`, `function`, `type`, `tag`, `attribute`, `operator`); a custom `Theme` may override any of them, and may set `syntax.block` (e.g. `"on #111c2e"`) to shade code blocks inside Markdown, and `repr.background` to give `print_obj` output its own background.
