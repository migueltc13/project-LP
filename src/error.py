"""
Compiler diagnostic utilities.

Provides modern compiler-style error and warning reporting.

Example:

    _print_error(
        error="label 100 referenced but not defined",
        line="      GOTO 100",
        lineno=12,
        col_start=12,
        length=3
    )

Output:

    error: label 100 referenced but not defined
      --> line 12
       |
    12 |       GOTO 100
       |            ^^^
"""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass


# ANSI color codes for terminal output

_RED    = "\033[31m"
_YELLOW = "\033[33m"
_BLUE   = "\033[34m"
_CYAN   = "\033[36m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"


###
# Helpers
###

def get_source_line(obj, lineno: int) -> str:
    """
    Return the source line for a diagnostic.

    Arguments:
        obj: An object with a `source_lines` attribute containing the source
             code lines. Either lexer or parser objects can be used.
        lineno: The 1-based line number to retrieve.

    Returns:
        str: The source line at the given line number, or an empty string if
             out of range.
    """

    try:
        return obj.source_lines[lineno - 1]
    except (AttributeError, IndexError):
        return ""


def get_token_column(t, lexdata: Optional[str] = None) -> int:
    """
    Return the 1-based column where token/symbol t starts.

    In lexer callbacks, t usually has t.lexer.lexdata.
    In parser callbacks, p.slice[i] may not have .lexer, so callers should pass
    p.lexer.lexdata explicitly.
    """

    if lexdata is None:
        lexer = getattr(t, "lexer", None)
        lexdata = getattr(lexer, "lexdata", None)

    if lexdata is None:
        return 1

    lexpos = getattr(t, "lexpos", None)

    if lexpos is None:
        return 1

    line_start = lexdata.rfind("\n", 0, lexpos) + 1
    return lexpos - line_start + 1


def get_parser_eof_location(parser) -> tuple[str, int, int]:
    """
    Return the source line, line number, and column for an EOF diagnostic.

    The column points just after the final character of the final source line.
    """

    if parser.source_lines:
        lineno = len(parser.source_lines)
        line = parser.source_lines[-1]
        col_start = len(line) + 1
    else:
        lineno = 1
        line = ""
        col_start = 1

    return line, lineno, col_start


###
# Diagnostics
###

@dataclass(frozen=True)
class Diagnostic:
    error: str
    line: str
    lineno: int
    col_start: int
    length: int
    warning: bool = False
    hint: Optional[str] = None
    filename: Optional[str] = None


def flush_diagnostics(*objects, stream=None) -> None:
    """
    Print all stored diagnostics from the given objects in source order.

    Sorting order:
        1. line
        2. column
        3. underline length
        4. severity, errors before warnings
        5. message, for deterministic output
    """

    def diagnostic_sort_key(diagnostic: Diagnostic):
        severity_rank = 1 if diagnostic.warning else 0

        return (
            diagnostic.lineno,
            diagnostic.col_start,
            diagnostic.length,
            severity_rank,
            diagnostic.error,
        )

    diagnostics = []

    for obj in objects:
        diagnostics.extend(getattr(obj, "diagnostics", []))

    sorted_diagnostics = sorted(diagnostics, key=diagnostic_sort_key)

    for i, diagnostic in enumerate(sorted_diagnostics):
        _print_error(
            error=diagnostic.error,
            line=diagnostic.line,
            lineno=diagnostic.lineno,
            col_start=diagnostic.col_start,
            length=diagnostic.length,
            warning=diagnostic.warning,
            hint=diagnostic.hint,
            filename=diagnostic.filename,
            stream=stream,
        )

        if i < len(sorted_diagnostics) - 1:
            print(file=stream)


def record_diagnostic(
    obj,
    *,
    error: str,
    line: str,
    lineno: int,
    col_start: int,
    length: int,
    warning: bool = False,
    hint: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    """
    Store a diagnostic in obj.diagnostics instead of printing it immediately.

    obj is usually the lexer or parser.
    """

    if not hasattr(obj, "diagnostics"):
        obj.diagnostics = []

    obj.diagnostics.append(
        Diagnostic(
            error=error,
            line=line,
            lineno=lineno,
            col_start=col_start,
            length=length,
            warning=warning,
            hint=hint,
            filename=filename,
        )
    )

    if not warning and hasattr(obj, "has_error"):
        obj.has_error = True


def record_parser_token_error(
    parser,
    token,
    *,
    message: str,
    hint: Optional[str] = None,
    warning: Optional[bool] = False,
) -> None:
    """
    Record a semantic diagnostic attached to a parser token.
    """

    record_diagnostic(
        parser,
        error=message,
        line=get_source_line(parser, token.lineno),
        lineno=token.lineno,
        col_start=get_token_column(token),
        length=max(1, len(str(token.value))),
        warning=warning,
        filename=parser.source_filename,
        hint=hint,
    )


def record_node_error(
    parser,
    node,
    *,
    message: str,
    hint: Optional[str] = None,
    warning: Optional[bool] = False,
) -> None:
    """
    Record a diagnostic attached to an AST node with a SourceLocation.
    """

    location = getattr(node, "location", None)

    if location is None:
        record_diagnostic(
            parser,
            error=message,
            line="",
            lineno=1,
            col_start=1,
            length=1,
            warning=warning,
            filename=parser.source_filename,
            hint=hint,
        )
        return

    record_diagnostic(
        parser,
        error=message,
        line=get_source_line(parser, location.lineno),
        lineno=location.lineno,
        col_start=location.col_start,
        length=location.length,
        warning=warning,
        filename=parser.source_filename,
        hint=hint,
    )


def record_syntax_error(parser, token) -> None:
    """
    Record a parser syntax error diagnostic.

    If token is None, report unexpected EOF.
    Otherwise, report the unexpected token location.
    """

    if token is None:
        line, lineno, col_start = get_parser_eof_location(parser)

        record_diagnostic(
            parser,
            error="unexpected end of file",
            line=line,
            lineno=lineno,
            col_start=col_start,
            length=1,
            filename=parser.source_filename,
            hint="perhaps you forgot the END statement",
        )

        return

    record_diagnostic(
        parser,
        error=f"syntax error at token {token.value!r}",
        line=get_source_line(parser, token.lineno),
        lineno=token.lineno,
        col_start=get_token_column(token),
        length=max(1, len(str(token.value))),
        filename=parser.source_filename,
    )


def record_label_diagnostic(
    parser,
    *,
    message: str,
    location: dict,
    warning: bool = False,
) -> None:
    """
    Record a label diagnostic using stored location metadata.
    """

    lineno = location["lineno"]
    col_start = location["col_start"]
    length = location["length"]

    record_diagnostic(
        parser,
        error=message,
        line=get_source_line(parser, lineno),
        lineno=lineno,
        col_start=col_start,
        length=length,
        warning=warning,
        filename=parser.source_filename,
    )


###
# Printing errors
###


def _print_error(
    error: str,
    line: str,
    lineno: int,
    col_start: int,
    length: int,
    *,
    warning: bool = False,
    hint: Optional[str] = None,
    filename: Optional[str] = None,
    stream=None,
    use_color: Optional[bool] = None,
) -> None:
    """
    Print a compiler-style diagnostic.

    Arguments:
        error: The error or warning message.
        line: The source code line where the problem occurred.
        lineno: The 1-based line number.
        col_start: The 1-based column where the problem starts.
        length: The number of characters to underline.
        warning: If True, print as a warning instead of an error.
        hint: Optional help text printed below the caret marker.
        filename: Optional source filename.
        stream: Optional output stream. Defaults to stderr.
        use_color: Force color on/off. Defaults to terminal detection.
    """

    import sys

    def color(text: str, color_code: str, *, enabled: bool) -> str:
        """
        Apply an ANSI color if enabled.
        """

        if not enabled:
            return text

        return f"{color_code}{text}{_RESET}"

    if stream is None:
        stream = sys.stderr

    if use_color is None:
        use_color = sys.stderr.isatty()

    if lineno < 1:
        lineno = 1

    if col_start < 1:
        col_start = 1

    if length < 1:
        length = 1

    clean_line = line.rstrip("\n")

    # Clamp the marker position so diagnostics do not crash on bad metadata.
    if len(clean_line) == 0:
        col_start = 1
    elif col_start > len(clean_line) + 1:
        col_start = len(clean_line) + 1

    kind = "warning" if warning else "error"
    kind_color = _YELLOW if warning else _RED

    colored_kind = color(kind, kind_color + _BOLD, enabled=use_color)
    colored_message = color(error, _BOLD, enabled=use_color)
    colored_arrow = color("-->", _BLUE, enabled=use_color)

    line_number_text = str(lineno)
    gutter_width = len(line_number_text)

    location = f"line {lineno}"
    if filename is not None:
        location = f"{filename}:{lineno}:{col_start}"

    pointer_padding = " " * (col_start - 1)
    pointer = "^" * length
    colored_pointer = color(pointer, kind_color + _BOLD, enabled=use_color)

    print(f"{colored_kind}: {colored_message}", file=stream)
    print(f"{' ' * gutter_width} {colored_arrow} {location}", file=stream)
    print(f"{' ' * gutter_width} |", file=stream)
    print(f"{line_number_text} | {clean_line}", file=stream)
    print(f"{' ' * gutter_width} | {pointer_padding}{colored_pointer}", file=stream)

    if hint is not None:
        colored_hint_label = color("hint", _CYAN + _BOLD, enabled=use_color)
        colored_hint = color(hint, _CYAN, enabled=use_color)
        print(f"{' ' * gutter_width} = {colored_hint_label}: {colored_hint}", file=stream)
