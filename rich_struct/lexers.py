"""Pygments lexers that re-tag JSON, YAML and XML tokens, and Jinja tags, so a theme can colour them in detail.

Data tokens become children of the token pygments gave them (``Punctuation`` -> ``Punctuation.Data``), and Jinja
tokens are ``Token.Jinja.*``. Both are only produced for themes that style them, so other themes are unaffected.
"""

import re
from typing import Container, Iterable, Iterator, List, Optional, Tuple

from pygments.filter import Filter
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Keyword, Literal, Name, Number, Operator, Punctuation, String, Token, _TokenType
from pygments.util import ClassNotFound

Tokens = Iterable[Tuple[_TokenType, str]]
JINJA = Token.Jinja
_JINJA_TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)
_HAS_JINJA = re.compile(r"\{[{%#]")
_YAML_NUMBER = re.compile(
    r"[-+]?(?:\d[\d_]*(?:\.\d*)?(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?|0x[0-9a-fA-F_]+|0o[0-7_]+|\.(?:inf|Inf|INF))"
    r"|\.(?:nan|NaN|NAN)"
)
_YAML_CONSTANT = re.compile(r"null|Null|NULL|~|true|True|TRUE|false|False|FALSE")


def themed_lexer(name: str, code: str, styled: Container[_TokenType]) -> Optional[Lexer]:
    """A lexer for ``name`` with re-tagged tokens, or None when the theme has nothing to gain from one.

    ``styled`` holds the tokens the theme colours. With ``Punctuation.Data`` among them, JSON, YAML and XML get
    their data tokens re-tagged. With ``Token.Jinja.Variable``, Jinja tags are lexed too: YAML, XML and HTML
    switch to pygments' Jinja-aware lexers when ``code`` has a tag, and tags inside JSON and Python strings
    (not f-strings) are picked out.
    """
    try:
        alias = get_lexer_by_name(name).aliases[0]
    except ClassNotFound:
        return None
    data = Punctuation.Data in styled and alias in ("json", "yaml", "xml")
    jinja = JINJA.Variable in styled and (
        alias in ("json", "python") or (alias in ("yaml", "xml", "html") and bool(_HAS_JINJA.search(code)))
    )
    if not (data or jinja):
        return None
    lexer = get_lexer_by_name(f"{alias}+jinja" if jinja and alias in ("yaml", "xml", "html") else alias)
    lexer.add_filter(_Retag(alias, data, jinja))
    return lexer


def jinja_spans(text: str) -> Iterator[Tuple[int, int, _TokenType]]:
    """``(start, end, token)`` for every Jinja tag in ``text`` (JSON strings from rich's JSON highlighter)."""
    for match in _JINJA_TAG.finditer(text):
        pos = match.start()
        for ttype, value in _lex_jinja(match.group()):
            yield pos, pos + len(value), ttype
            pos += len(value)


class _Retag(Filter):
    def __init__(self, alias: str, data: bool, jinja: bool) -> None:
        super().__init__()
        self.alias, self.data, self.jinja = alias, data, jinja

    def filter(self, lexer: Optional[Lexer], stream: Tokens) -> Iterator[Tuple[_TokenType, str]]:
        tokens: Tokens = stream
        if self.jinja:
            tokens = _retag_jinja(_jinja_in_strings(tokens) if self.alias in ("json", "python") else tokens)
        if self.data:
            tokens = {"yaml": lambda t: _yaml(list(t)), "xml": _xml, "json": _json}[self.alias](tokens)
        yield from tokens


def _key(depth: int) -> _TokenType:
    """A key ``depth`` objects or mappings deep (0: top level); themes colour 5 levels, then repeat."""
    return getattr(Name.Tag, f"Level{max(depth, 0) % 5}")


def _json(tokens: Tokens) -> Iterator[Tuple[_TokenType, str]]:
    opened: List[str] = []  # { and [ not yet closed; only objects count towards a key's depth, as in VS Code
    for ttype, value in tokens:
        if ttype in Punctuation:
            for char in value:  # pygments joins neighbours: "]}"
                if char in "{[":
                    opened.append(char)
                elif char in "}]" and opened:
                    opened.pop()
            ttype = Punctuation.Data
        elif ttype in Number:
            ttype = Number.Data
        elif ttype in Keyword.Constant:
            ttype = Keyword.Constant.Data
        elif ttype is Name.Tag and len(value) > 1:  # "key": quotes apart, still keys elsewhere
            yield Name.Tag.Punctuation, value[0]
            yield _key(opened.count("{") - 1), value[1:-1]
            ttype, value = Name.Tag.Punctuation, value[-1]
        yield ttype, value


def _yaml(tokens: List[Tuple[_TokenType, str]]) -> Iterator[Tuple[_TokenType, str]]:
    plain = (Literal.Scalar.Plain, Name.Variable)  # flow values ([a, 1]) come as Name.Variable

    def beside(i: int, step: int) -> Optional[_TokenType]:
        """The token type next to ``tokens[i]`` on its line, skipping spaces."""
        i += step
        while 0 <= i < len(tokens) and not tokens[i][1].strip(" \t"):
            i += step
        return tokens[i][0] if 0 <= i < len(tokens) else None

    # a key's depth is the number of mappings around it, as in VS Code (lists don't count): block mappings by
    # indentation, flow mappings ({...}) by nesting
    block: List[int] = []  # columns of the block keys whose values hold the current line
    flow: List[str] = []  # { and [ not yet closed
    column = 0
    for i, (ttype, value) in enumerate(tokens):
        start = column
        column = len(value) - value.rfind("\n") - 1 if "\n" in value else column + len(value)
        if ttype is Name.Tag:
            if flow:
                ttype = _key(len(block) + flow.count("{") - 1)
            else:
                at = start + len(value) - len(value.lstrip())
                while block and block[-1] >= at:
                    block.pop()
                ttype = _key(len(block))
                block.append(at)
        elif ttype is Punctuation:
            ttype = Punctuation.Data
        elif ttype is Punctuation.Indicator and value == "-" and not flow:  # a list item ends the keys right of it
            while block and block[-1] >= start:
                block.pop()
        elif ttype is Punctuation.Indicator and value != "-":
            if value in "{[":
                flow.append(value)
            elif value in "}]" and flow:
                flow.pop()
            ttype = Punctuation.Indicator.Data
        elif ttype is Name.Namespace:  # --- and ...: a new document
            block.clear()
            flow.clear()
            ttype = Name.Namespace.Data
        elif ttype is Name.Variable and value.startswith("*"):
            ttype = Name.Variable.Alias
        elif ttype in (Name.Label, Keyword.Type):  # &anchor, !!tag
            ttype = ttype.Data
        elif ttype is Name.Constant:  # block scalar lines
            ttype = Name.Constant.Data
        elif ttype in String and value in ("\"", "'"):
            ttype = String.Delimiter.Data
        elif ttype in plain:
            # a number or constant only when it is the whole value, not a word in "3 apples"
            alone = beside(i, -1) not in plain and beside(i, 1) not in plain
            if alone and _YAML_NUMBER.fullmatch(value):
                ttype = ttype.Number
            elif alone and _YAML_CONSTANT.fullmatch(value):
                ttype = ttype.Constant
            elif ttype is Name.Variable:
                ttype = Name.Variable.Plain
        yield ttype, value


def _xml(tokens: Tokens) -> Iterator[Tuple[_TokenType, str]]:
    for ttype, value in tokens:
        tag = re.findall(r"</?|/?>|[^\s</>:]+:|[^\s</>]+|\s+", value) if ttype is Name.Tag else []  # <ns:root, />
        attr = re.findall(r"[^\s=:]+:|=|[^=:]+", value) if ttype is Name.Attribute else []  # xmlns:ns=
        if "".join(tag) == value and tag:
            for part in tag:
                yield (
                    Name.Tag.Punctuation if part[0] in "</>"
                    else Name.Tag.Namespace if part.endswith(":")
                    else Name.Tag.Element if part.strip() else Name.Tag
                ), part
        elif "".join(attr) == value and attr:
            for part in attr:
                yield (Name.Attribute.Namespace if part.endswith(":") else Name.Attribute.Punctuation if part == "=" else ttype), part
        elif ttype in String and value in ("\"", "'"):  # quotes around a value that holds Jinja
            yield String.Delimiter.Data, value
        elif ttype in String and value[:1] == value[-1:] and value[:1] in "\"'" and len(value) > 1:
            yield String.Delimiter.Data, value[0]
            yield ttype, value[1:-1]
            yield String.Delimiter.Data, value[-1]
        elif ttype is Comment.Preproc and value.startswith("<?"):
            yield Comment.Preproc.Prolog, value
        elif ttype is Comment.Preproc and value.startswith("<![CDATA["):
            yield Comment.Preproc.Cdata, value
        elif ttype is Name.Entity:
            yield Name.Entity.Data, value
        else:
            yield ttype, value


def _lex_jinja(tag: str) -> List[Tuple[_TokenType, str]]:
    return list(_retag_jinja(get_lexer_by_name("jinja", stripnl=False, ensurenl=False).get_tokens(tag)))


def _jinja_in_strings(tokens: Tokens) -> Iterator[Tuple[_TokenType, str]]:
    """Joins each string's pieces (pygments splits them at braces and %) and lexes the Jinja tags in it."""
    run: List[Tuple[_TokenType, str]] = []
    fstring = False

    def flush() -> Iterator[Tuple[_TokenType, str]]:
        text = "".join(v for _, v in run)
        if fstring or not _JINJA_TAG.search(text):  # in f-strings {{ is an escaped brace
            yield from run
        else:
            kind, pos = run[0][0], 0
            for match in _JINJA_TAG.finditer(text):
                if match.start() > pos:
                    yield kind, text[pos : match.start()]
                yield from _lex_jinja(match.group())
                pos = match.end()
            if pos < len(text):
                yield kind, text[pos:]
        run.clear()

    for ttype, value in tokens:
        if ttype in String and ttype is not String.Affix:
            run.append((ttype, value))
            continue
        yield from flush()
        fstring = ttype is String.Affix and "f" in value.lower()
        yield ttype, value
    yield from flush()


def _retag_jinja(tokens: Tokens) -> Iterator[Tuple[_TokenType, str]]:
    """Pygments' Jinja tokens (Comment.Preproc delimiters, Keyword, Name.Variable...) as ``Token.Jinja.*``."""
    inside = False
    pending: List[Tuple[_TokenType, str]] = []  # a name, until we know whether "(" follows (a function call)
    for ttype, value in tokens:
        if ttype is Comment.Preproc and value[:2] in ("{{", "{%"):
            inside = True
            yield JINJA.Delimiter, value
            continue
        if not inside:
            yield ttype, value
            continue
        if ttype is Comment.Preproc:  # }} or %}
            yield from pending
            pending.clear()
            inside = False
            yield JINJA.Delimiter, value
        elif ttype in Name.Variable:
            yield from pending
            pending[:] = [(JINJA.Delimiter, value[:1]), (JINJA.Variable, value[1:])] if value[:1] == "." else [(JINJA.Variable, value)]
        else:
            if pending and ttype is Operator and value.startswith("("):
                pending[-1] = (JINJA.Filter, pending[-1][1])
            yield from pending
            pending.clear()
            if ttype in Keyword:
                yield JINJA.Keyword, value
            elif ttype in Name.Function:
                yield JINJA.Filter, value
            elif ttype in String or ttype in Number:
                yield JINJA.Literal, value
            else:  # operators, punctuation, whitespace, the - of {%-
                yield JINJA.Delimiter, value
    yield from pending
