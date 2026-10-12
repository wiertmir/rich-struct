"""Theme palettes and their translation into rich ``Theme`` objects."""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
)
from rich.style import Style
from rich.syntax import ANSISyntaxTheme, SyntaxTheme
from rich.theme import Theme


class ThemeName(str, Enum):
    # dark
    TOKYO_NIGHT = "Tokyo Night"
    DRACULA = "Dracula"
    ONE_DARK_PRO = "One Dark Pro"
    MONOKAI = "Monokai"
    NORD = "Nord"
    GRUVBOX_DARK = "Gruvbox Dark"
    CATPPUCCIN_MOCHA = "Catppuccin Mocha"
    SOLARIZED_DARK = "Solarized Dark"
    GITHUB_DARK = "GitHub Dark"
    NIGHT_OWL = "Night Owl"
    WINTER_IS_COMING = "Winter is Coming"
    DARK_MODERN = "Dark Modern"
    MIDNIGHT_SLATE = "Midnight Slate"
    # light
    GITHUB_LIGHT = "GitHub Light"
    SOLARIZED_LIGHT = "Solarized Light"
    ONE_LIGHT = "One Light"
    CATPPUCCIN_LATTE = "Catppuccin Latte"
    GRUVBOX_LIGHT = "Gruvbox Light"
    TOKYO_NIGHT_LIGHT = "Tokyo Night Light"
    AYU_LIGHT = "Ayu Light"
    NIGHT_OWL_LIGHT = "Night Owl Light"
    LIGHT_PLUS = "Light+"
    EVERFOREST_LIGHT = "Everforest Light"
    LIGHT_MODERN = "Light Modern"
    PAPER_FROST = "Paper Frost"

    @property
    def is_dark(self) -> bool:
        return self in _DARK

    @property
    def theme(self) -> Theme:
        return _build(self)


# The ThemeName values again, spelled out so editors can autocomplete theme="...".
# Static type checkers can't derive this from the enum; a test keeps the two in sync.
ThemeLiteral = Literal[
    "Tokyo Night",
    "Dracula",
    "One Dark Pro",
    "Monokai",
    "Nord",
    "Gruvbox Dark",
    "Catppuccin Mocha",
    "Solarized Dark",
    "GitHub Dark",
    "Night Owl",
    "Winter is Coming",
    "Dark Modern",
    "Midnight Slate",
    "GitHub Light",
    "Solarized Light",
    "One Light",
    "Catppuccin Latte",
    "Gruvbox Light",
    "Tokyo Night Light",
    "Ayu Light",
    "Night Owl Light",
    "Light+",
    "Everforest Light",
    "Light Modern",
    "Paper Frost",
]

DEFAULT_THEME = ThemeName.MIDNIGHT_SLATE

T = ThemeName
#                       bg     fg     comment   red       orange    yellow    green     cyan      blue      purple
_PALETTES = {
    T.TOKYO_NIGHT:       "1a1b26 c0caf5 565f89 f7768e ff9e64 e0af68 9ece6a 7dcfff 7aa2f7 bb9af7",
    T.DRACULA:           "282a36 f8f8f2 6272a4 ff5555 ffb86c f1fa8c 50fa7b 8be9fd bd93f9 ff79c6",
    T.ONE_DARK_PRO:      "282c34 abb2bf 5c6370 e06c75 d19a66 e5c07b 98c379 56b6c2 61afef c678dd",
    T.MONOKAI:           "272822 f8f8f2 75715e f92672 fd971f e6db74 a6e22e a1efe4 66d9ef ae81ff",
    T.NORD:              "2e3440 d8dee9 616e88 bf616a d08770 ebcb8b a3be8c 88c0d0 81a1c1 b48ead",
    T.GRUVBOX_DARK:      "282828 ebdbb2 928374 fb4934 fe8019 fabd2f b8bb26 8ec07c 83a598 d3869b",
    T.CATPPUCCIN_MOCHA:  "1e1e2e cdd6f4 6c7086 f38ba8 fab387 f9e2af a6e3a1 89dceb 89b4fa cba6f7",
    T.SOLARIZED_DARK:    "002b36 839496 586e75 dc322f cb4b16 b58900 859900 2aa198 268bd2 6c71c4",
    T.GITHUB_DARK:       "0d1117 c9d1d9 8b949e ff7b72 ffa657 e3b341 7ee787 a5d6ff 79c0ff d2a8ff",
    T.NIGHT_OWL:         "011627 d6deeb 637777 ef5350 f78c6c ecc48d addb67 7fdbca 82aaff c792ea",
    T.WINTER_IS_COMING:  "011627 a7dbf7 999999 ef5350 8dec95 f7ecb5 bcf0c0 7fdbca 87aff4 00bff9",
    T.DARK_MODERN:       "1f1f1f cccccc 6a9955 f44747 ce9178 dcdcaa b5cea8 4ec9b0 569cd6 c586c0",
    T.MIDNIGHT_SLATE:    "0b1320 d1d5db 64748b fb7185 fbbf24 fcd34d a3e635 22d3ee 7dd3fc a78bfa",
    T.GITHUB_LIGHT:      "ffffff 24292f 6e7781 cf222e 953800 9a6700 116329 1b7c83 0550ae 8250df",
    T.SOLARIZED_LIGHT:   "fdf6e3 657b83 93a1a1 dc322f cb4b16 b58900 859900 2aa198 268bd2 6c71c4",
    T.ONE_LIGHT:         "fafafa 383a42 a0a1a7 e45649 986801 c18401 50a14f 0184bc 4078f2 a626a4",
    T.CATPPUCCIN_LATTE:  "eff1f5 4c4f69 9ca0b0 d20f39 fe640b df8e1d 40a02b 04a5e5 1e66f5 8839ef",
    T.GRUVBOX_LIGHT:     "fbf1c7 3c3836 928374 9d0006 af3a03 b57614 79740e 427b58 076678 8f3f71",
    T.TOKYO_NIGHT_LIGHT: "d5d6db 343b58 9699a3 8c4351 965027 8f5e15 485e30 0f4b6e 34548a 5a4a78",
    T.AYU_LIGHT:         "fafafa 5c6166 abb0b6 f07171 fa8d3e f2ae49 86b300 4cbf99 399ee6 a37acc",
    T.NIGHT_OWL_LIGHT:   "fbfbfb 403f53 989fb1 de3d3b c96765 daaa01 08916a 0c969b 4876d6 994cc3",
    T.LIGHT_PLUS:        "ffffff 000000 008000 a31515 811f3f 795e26 098658 267f99 0000ff af00db",
    T.EVERFOREST_LIGHT:  "fdf6e3 5c6a72 939f91 f85552 f57d26 dfa000 8da101 35a77c 3a94c5 df69ba",
    T.LIGHT_MODERN:      "ffffff 3b3b3b 008000 a31515 811f3f 795e26 098658 267f99 0000ff af00db",
    T.PAPER_FROST:       "fafaf7 263238 64748b be123c b45309 a16207 15803d 0e7490 0369a1 7c3aed",
}
_DARK = frozenset(list(T)[:13])
# Borders, rules and captions use the comment colour, except where comments are green.
_MUTED = {T.DARK_MODERN: "#6e7681", T.LIGHT_MODERN: "#767676", T.LIGHT_PLUS: "#767676"}
# Styles that differ from what the palette alone would give (applied on top in _build).
_OVERRIDES = {
    T.MIDNIGHT_SLATE: {
        "syntax.tag": "#7dd3fc",
        "syntax.block": "on #111c2e",
        "markdown.h1": "bold #5eead4",
        "markdown.h2": "bold #22d3ee",
        "markdown.h3": "bold #7dd3fc",
        "markdown.h4": "bold #a5b4fc",
        "markdown.h5": "#a5b4fc",
        "markdown.h6": "dim #a5b4fc",
        "markdown.strong": "bold #f8fafc",
        "markdown.em": "italic #c4b5fd",
        "markdown.emph": "italic #c4b5fd",
        "markdown.s": "strike #64748b",
        "markdown.code": "#fbbf24 on #111c2e",
        "markdown.block_quote": "italic #86efac",
        "markdown.item.bullet": "bold #fbbf24",
        "markdown.item.number": "bold #fbbf24",
        "markdown.link": "underline #38bdf8",
        "markdown.link_url": "underline #38bdf8",  # rich styles link text with link_url
        "markdown.hr": "#475569",
        "json.brace": "#94a3b8",
        "json.key": "#7dd3fc",
        "json.bool_true": "bold #22d3ee",
        "json.bool_false": "bold #22d3ee",
        "json.null": "italic #a78bfa",
        # objects (print_obj)
        "repr.background": "on #0f172a",
        "repr.attrib_name": "#cbd5e1",
        "repr.call": "bold #22d3ee",
        "repr.str": "#a3e635",
        "repr.number": "#fbbf24",
        "repr.number_complex": "#fbbf24",
        "repr.none": "italic #c4b5fd",
        "repr.bool_true": "italic #86efac",
        "repr.bool_false": "italic #86efac",
        "repr.tag_name": "#86efac",  # enum members print as <Role.ADMIN: 1>
        "repr.attrib_equal": "#f8fafc",
        "repr.brace": "#94a3b8",
        "repr.comma": "#94a3b8",
        "repr.tag_start": "#94a3b8",
        "repr.tag_end": "#94a3b8",
    },
    T.PAPER_FROST: {
        "syntax.tag": "#0369a1",
        "syntax.block": "on #f1f5f9",
        "markdown.h1": "bold #0f766e",
        "markdown.h2": "bold #0e7490",
        "markdown.h3": "bold #0369a1",
        "markdown.h4": "bold #4f46e5",
        "markdown.h5": "#4f46e5",
        "markdown.h6": "dim #4f46e5",
        "markdown.strong": "bold #111827",
        "markdown.em": "italic #7c3aed",
        "markdown.emph": "italic #7c3aed",
        "markdown.s": "strike #9ca3af",
        "markdown.code": "#c2410c on #f1f5f9",
        "markdown.block_quote": "italic #15803d",
        "markdown.item.bullet": "bold #b45309",
        "markdown.item.number": "bold #b45309",
        "markdown.link": "underline #2563eb",
        "markdown.link_url": "underline #2563eb",  # rich styles link text with link_url
        "markdown.hr": "#cbd5e1",
        "json.brace": "#64748b",
        "json.key": "#0369a1",
        "json.bool_true": "bold #0e7490",
        "json.bool_false": "bold #0e7490",
        "json.null": "italic #7c3aed",
        # objects (print_obj)
        "repr.background": "on #ffffff",
        "repr.attrib_name": "#1f2937",
        "repr.call": "bold #2563eb",
        "repr.str": "#16853a",
        "repr.number": "#b45309",
        "repr.number_complex": "#b45309",
        "repr.none": "italic #7c3aed",
        "repr.bool_true": "italic #059669",
        "repr.bool_false": "italic #059669",
        "repr.tag_name": "#059669",  # enum members print as <Role.ADMIN: 1>
        "repr.attrib_equal": "#111111",
        "repr.brace": "#475569",
        "repr.comma": "#475569",
        "repr.tag_start": "#475569",
        "repr.tag_end": "#475569",
    },
}
del T

# pygments token -> name of the "syntax.*" style that colours it
_TOKENS = {
    Token: "text",
    Comment: "comment",
    Keyword: "keyword",
    Keyword.Constant: "number",
    Keyword.Type: "type",
    Name.Function: "function",
    Name.Class: "type",
    Name.Builtin: "type",
    Name.Tag: "tag",
    Name.Attribute: "attribute",
    Name.Decorator: "attribute",
    Name.Constant: "number",
    String: "string",
    String.Escape: "operator",
    Number: "number",
    Operator: "operator",
    Generic.Deleted: "tag",
    Generic.Inserted: "string",
    Generic.Heading: "function",
    Error: "tag",
}


def _distance(a: str, b: str) -> float:
    """Perceptual ("redmean") distance between two #rrggbb colours; about 765 for black vs white."""
    (r1, g1, b1), (r2, g2, b2) = ([int(c[i : i + 2], 16) for i in (1, 3, 5)] for c in (a, b))
    red = (r1 + r2) / 2
    return (
        (2 + red / 256) * (r1 - r2) ** 2 + 4 * (g1 - g2) ** 2 + (2 + (255 - red) / 256) * (b1 - b2) ** 2
    ) ** 0.5


@lru_cache(maxsize=None)
def _build(name: ThemeName) -> Theme:
    bg, fg, comment, red, orange, yellow, green, cyan, blue, purple = (
        "#" + c for c in _PALETTES[name].split()
    )
    muted = _MUTED.get(name, comment)
    # list bullets and numbers: the accent that stands out most from the text and from bold text
    marker = max((blue, purple, cyan), key=lambda c: min(_distance(c, fg), _distance(c, orange)))
    styles = {
        "background": f"{fg} on {bg}",
        # code (see _TOKENS)
        "syntax.text": fg,
        "syntax.comment": f"italic {comment}",
        "syntax.keyword": purple,
        "syntax.string": green,
        "syntax.number": orange,
        "syntax.function": blue,
        "syntax.type": cyan,
        "syntax.tag": red,
        "syntax.attribute": yellow,
        "syntax.operator": cyan,
        # markdown
        "markdown.paragraph": fg,
        "markdown.text": fg,
        "markdown.h1": f"bold {purple}",
        "markdown.h1.border": muted,
        "markdown.h2": f"bold {blue}",
        "markdown.h3": f"bold {cyan}",
        "markdown.h4": f"bold {green}",
        "markdown.h5": f"bold {yellow}",
        "markdown.h6": f"italic {comment}",
        "markdown.h7": f"italic {comment}",
        "markdown.strong": f"bold {orange}",
        "markdown.em": f"italic {yellow}",
        "markdown.emph": f"italic {yellow}",
        "markdown.s": f"strike {comment}",
        "markdown.code": green,
        "markdown.code_block": fg,
        "markdown.block_quote": f"italic {comment}",
        "markdown.item": fg,
        "markdown.item.bullet": f"bold {marker}",
        "markdown.item.number": f"bold {marker}",
        "markdown.hr": muted,
        "markdown.link": blue,
        "markdown.link_url": f"underline {cyan}",
        "markdown.table.border": muted,
        "markdown.table.header": f"bold {blue}",
        # json
        "json.key": f"bold {blue}",
        "json.str": green,
        "json.number": orange,
        "json.bool_true": f"italic {orange}",
        "json.bool_false": f"italic {orange}",
        "json.null": f"italic {purple}",
        "json.brace": f"bold {fg}",
        # repr / pretty-printed objects
        "repr.str": green,
        "repr.number": orange,
        "repr.number_complex": orange,
        "repr.bool_true": f"italic {orange}",
        "repr.bool_false": f"italic {orange}",
        "repr.none": f"italic {purple}",
        "repr.brace": f"bold {fg}",
        "repr.comma": fg,
        "repr.ellipsis": muted,
        "repr.indent": f"dim {muted}",
        "repr.tag_start": fg,
        "repr.tag_name": f"bold {red}",
        "repr.tag_contents": fg,
        "repr.tag_end": fg,
        "repr.attrib_name": yellow,
        "repr.attrib_equal": cyan,
        "repr.attrib_value": purple,
        "repr.call": f"bold {blue}",
        "repr.url": f"underline {cyan}",
        "repr.path": cyan,
        "repr.filename": f"bold {cyan}",
        "repr.uuid": yellow,
        "repr.ipv4": green,
        "repr.ipv6": green,
        "repr.eui48": green,
        "repr.eui64": green,
        "repr.error": f"bold {red}",
        # misc rich output
        "table.header": f"bold {blue}",
        "table.title": f"bold {purple}",
        "table.caption": f"italic {muted}",
        "rule.line": muted,
        "rule.text": blue,
        "pretty": fg,
    }
    styles.update(_OVERRIDES.get(name, {}))
    return Theme(styles)


class _SyntaxTheme(ANSISyntaxTheme):
    def __init__(self, style_map: dict, background: Style) -> None:
        super().__init__(style_map)
        self.background = background

    def get_background_style(self) -> Style:
        return self.background


def syntax_theme(theme: Theme, block: bool = False) -> SyntaxTheme:
    """Code-highlighting theme from a rich Theme's ``syntax.*`` styles.

    Styles the theme doesn't define fall back to the default theme's. With ``block``
    (code blocks inside Markdown) the theme's optional ``syntax.block`` style is the
    background.
    """
    fallback = _build(DEFAULT_THEME).styles
    styles = {
        name: theme.styles.get(f"syntax.{name}", fallback[f"syntax.{name}"])
        for name in set(_TOKENS.values())
    }
    background = theme.styles.get("syntax.block", Style.null()) if block else Style.null()
    return _SyntaxTheme({token: styles[name] for token, name in _TOKENS.items()}, background)
