"""Regenerate the README screenshots: python screenshots/make.py (needs google-chrome, numpy, pandas)."""

import io
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from rich.console import Console
from rich.terminal_theme import TerminalTheme
from rich.text import Text

import rich_struct as rs
from rich_struct import ThemeName

os.environ.update(FORCE_COLOR="1", COLORTERM="truecolor", COLUMNS="84")
OUT = Path(__file__).parent

MARKDOWN = """### 🌟 Top Recommendation: Build a Custom Discord Bot
If you use Discord with friends or clubs, this is the most rewarding project.

* **Languages to use:** Python (`discord.py`) or JavaScript (`discord.js`).
* **What you will learn:**
  * Asynchronous programming (`async`/`await`).
  * How to keep sensitive data safe using environment variables (`.env`).
* **Step-by-step roadmap:**
  1. **Level 1:** Make it respond to simple text commands.
  2. **Level 2:** Add a dice roller or a mini text-trivia game.

```python
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")  # replies to !ping
```
"""

JSON = {"name": "rich-struct", "version": 0.1, "tags": ["print", "theme"], "stable": False, "license": None}

YAML = """# deployment
service:
  name: api
  replicas: 3
  debug: false
  ports: [80, 443]
  image: "ghcr.io/acme/api:1.2"
"""

XML = """<?xml version="1.0"?>
<!-- catalogue -->
<catalog updated="2026-10-11">
  <book id="bk101" lang="en">
    <title>Printing structs</title>
    <price>44.95</price>
  </book>
</catalog>
"""

CODE = '''def fibonacci(n: int) -> list[int]:
    """First n Fibonacci numbers."""
    a, b, out = 0, 1, []
    for _ in range(n):  # iterative, no recursion
        out.append(a)
        a, b = b, a + b
    return out
'''


class Role(Enum):
    ADMIN = 1
    GUEST = 2


@dataclass
class User:
    name: str
    age: int
    active: bool = True
    email: Optional[str] = None
    role: Role = Role.ADMIN
    tags: List[str] = field(default_factory=list)


OBJECT = {"user": User("Ada", 36, tags=["admin", "dev"]), "url": "https://example.com/a?b=1", "pi": 3.14159}

RECORDS = [
    {"id": 1, "name": "Ada", "score": 91.5, "admin": True},
    {"id": 2, "name": "Linus", "score": 78.25, "admin": False},
    {"id": 3, "name": "Grace", "score": None, "admin": False},
]

ARRAY = np.random.default_rng(0).normal(size=(4, 5))

DF = pd.DataFrame(
    {
        "city": ["Kraków", "Oslo", "Lima"],
        "population": [804_237, 709_037, 10_092_000],
        "area_km2": [326.8, 454.0, 2672.3],
        "capital": [False, True, True],
        "twinned": pd.to_datetime(["1991-05-18", "2003-09-01", None]),
    }
).set_index("city")

SHOTS = [  # file name, theme, call
    ("markdown", ThemeName.MIDNIGHT_SLATE, lambda **kw: rs.print_md(MARKDOWN, **kw)),
    ("json", ThemeName.NORD, lambda **kw: rs.print_json(JSON, **kw)),
    ("yaml", ThemeName.ONE_DARK_PRO, lambda **kw: rs.print_yaml(YAML, **kw)),
    ("xml", ThemeName.GITHUB_DARK, lambda **kw: rs.print_xml(XML, **kw)),
    ("object", ThemeName.CATPPUCCIN_MOCHA, lambda **kw: rs.print_obj(OBJECT, **kw)),
    ("code", ThemeName.ONE_LIGHT, lambda **kw: rs.print_syntax(CODE, "python", **kw)),
    ("list", ThemeName.CATPPUCCIN_LATTE, lambda **kw: rs.print_table(RECORDS, **kw)),
    ("numpy", ThemeName.SOLARIZED_DARK, lambda **kw: rs.print_table(ARRAY, **kw)),
    ("dataframe", ThemeName.GITHUB_LIGHT, lambda **kw: rs.print_table(DF, title="Cities", **kw)),
    ("series", ThemeName.NIGHT_OWL, lambda **kw: rs.print_table(DF["area_km2"], **kw)),
]


def shoot(name: str, theme: ThemeName, call) -> None:
    ansi = io.StringIO()
    call(theme=theme, file=ansi)
    base = theme.theme.styles["background"]
    bg, fg = base.bgcolor.get_truecolor(), base.color.get_truecolor()
    console = Console(record=True, width=84, file=io.StringIO(), force_terminal=True, color_system="truecolor")
    console.print(Text.from_ansi(ansi.getvalue()))
    svg = console.export_svg(title=theme.value, theme=TerminalTheme(bg, fg, [fg] * 8))
    width, height = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "shot.svg").write_text(svg)
        subprocess.run(
            ["google-chrome", "--headless", "--hide-scrollbars", "--force-device-scale-factor=1.5",
             f"--window-size={int(width)},{int(height)}", "--default-background-color=00000000",
             f"--screenshot={OUT / (name + '.png')}", f"file://{tmp}/shot.svg"],
            check=True, capture_output=True,
        )


if __name__ == "__main__":
    for shot in SHOTS:
        shoot(*shot)
        print("wrote", shot[0])
