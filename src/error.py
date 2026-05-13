"""
Compiler diagnostic utilities.

Provides modern compiler-style error and warning reporting.

Example:

    print_error(
        error="label 100 referenced but not defined",
        line="      GOTO 100",
        lineno=12,
        col_start=12,
        length=3,
    )

Output:

    error: label 100 referenced but not defined
      --> line 12
       |
    12 |       GOTO 100
       |            ^^^
"""

from __future__ import annotations

import sys


_RED = "\033[31m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _supports_color() -> bool:
    """
    Return True if diagnostics should use ANSI colors.
    """

    return sys.stderr.isatty()


def _color(text: str, color_code: str, *, enabled: bool) -> str:
    """
    Apply an ANSI color if enabled.
    """

    if not enabled:
        return text

    return f"{color_code}{text}{_RESET}"


def print_error(
    error: str,
    line: str,
    lineno: int,
    col_start: int,
    length: int,
    *,
    warning: bool = False,
    hint: str | None = None,
    filename: str | None = None,
    stream=None,
    use_color: bool | None = None,
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

    if stream is None:
        stream = sys.stderr

    if use_color is None:
        use_color = _supports_color()

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

    colored_kind = _color(kind, kind_color + _BOLD, enabled=use_color)
    colored_message = _color(error, _BOLD, enabled=use_color)
    colored_arrow = _color("-->", _BLUE, enabled=use_color)

    line_number_text = str(lineno)
    gutter_width = len(line_number_text)

    location = f"line {lineno}"
    if filename is not None:
        location = f"{filename}:{lineno}:{col_start}"

    pointer_padding = " " * (col_start - 1)
    pointer = "^" * length
    colored_pointer = _color(pointer, kind_color + _BOLD, enabled=use_color)

    print(f"{colored_kind}: {colored_message}", file=stream)
    print(f"{' ' * gutter_width} {colored_arrow} {location}", file=stream)
    print(f"{' ' * gutter_width} |", file=stream)
    print(f"{line_number_text} | {clean_line}", file=stream)
    print(f"{' ' * gutter_width} | {pointer_padding}{colored_pointer}", file=stream)

    if hint is not None:
        colored_hint_label = _color("hint", _CYAN + _BOLD, enabled=use_color)
        colored_hint = _color(hint, _CYAN, enabled=use_color)
        print(f"{' ' * gutter_width} = {colored_hint_label}: {colored_hint}", file=stream)


def _get_source_line(parser, lineno: int) -> str:
    """
    Return the source line for a diagnostic.
    """

    if lineno < 1:
        return ""

    if lineno > len(parser.source_lines):
        return ""

    return parser.source_lines[lineno - 1]


def print_label_diagnostic(
    parser,
    *,
    message: str,
    location: dict,
    warning: bool = False,
) -> None:
    """
    Print a label diagnostic using stored location metadata.
    """

    lineno = location["lineno"]
    col_start = location["col_start"]
    length = location["length"]

    print_error(
        error=message,
        line=_get_source_line(parser, lineno),
        lineno=lineno,
        col_start=col_start,
        length=length,
        warning=warning,
        filename=parser.source_filename,
    )
