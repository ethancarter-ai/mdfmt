"""mdfmt — Markdown formatter CLI.

Normalize Markdown files: fix indentation, spacing, list markers, and
blank-line consistency. One command, zero runtime dependencies.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

LEADING_TABS = re.compile(r"^\t+")
TRAILING_SPACE = re.compile(r"[ \t]+$")
UNORDERED_LIST_RE = re.compile(r"^(\s*)([-*+])(\s.*|$)")
ORDERED_LIST_RE = re.compile(r"^(\s*)(\d+)\.(\s.*|$)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
FENCE_RE = re.compile(r"^(\s*)((?:[~]{3,}|`{3,}))(.*)$")
BLANK_RE = re.compile(r"^\s*$")


# ---------------------------------------------------------------------------
# Core formatting
# ---------------------------------------------------------------------------

def _strip_trailing(line: str) -> str:
    return TRAILING_SPACE.sub("", line)


def _expand_tabs(line: str, tab_width: int) -> str:
    """Expand only leading tabs; leave inner tabs untouched."""
    m = LEADING_TABS.match(line)
    if not m:
        return line
    leading = m.group(0)
    spaces = " " * (len(leading) * tab_width)
    return spaces + line[len(leading) :]


def _normalize_list_marker(line: str, marker: str) -> str:
    """Normalize unordered list markers to a single chosen character."""
    m = UNORDERED_LIST_RE.match(line)
    if not m:
        return line
    indent, _old, rest = m.group(1), m.group(2), m.group(3)
    return f"{indent}{marker}{rest}"


def _align_list_continuation(line: str, marker_indent: int, tab_width: int) -> str:
    """Align wrapped list item lines to the marker column.

    Only aligns lines that are a continuation of a list item (start with
    whitespace but are not themselves a list marker or heading or fence).
    """
    if not line or line[0] != " ":
        return line
    # Already a list item, heading, or fence? leave it.
    if UNORDERED_LIST_RE.match(line) or ORDERED_LIST_RE.match(line):
        return line
    if HEADING_RE.match(line):
        return line
    if FENCE_RE.match(line):
        return line
    if line.strip() == "":
        return line
    # Continuation line: pad to marker_indent + 2 (standard hanging indent)
    target = marker_indent + 2
    stripped = line.lstrip(" ")
    current_indent = len(line) - len(stripped)
    if current_indent < target:
        return " " * target + stripped
    return line


def _ensure_blank_before_heading(lines: list[str]) -> list[str]:
    """Ensure at least one blank line immediately before any heading line."""
    out: list[str] = []
    for i, line in enumerate(lines):
        if HEADING_RE.match(line):
            if out and out[-1].strip() != "":
                out.append("")
        out.append(line)
    return out


def _normalize_blanks(lines: list[str]) -> list[str]:
    """Collapse multiple blank lines to at most one, and strip trailing blanks."""
    collapsed: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue
        collapsed.append(line)
        prev_blank = is_blank
    # Strip trailing blank lines
    while collapsed and collapsed[-1].strip() == "":
        collapsed.pop()
    return collapsed


def _collect_list_indent(lines: list[str]) -> dict[int, int]:
    """Map line index -> list marker indent for list continuation alignment.

    Walks lines and records the indent of the most recent list item so
    continuation lines can align to it.
    """
    indents: dict[int, int] = {}
    last_indent = 0
    for idx, line in enumerate(lines):
        m = UNORDERED_LIST_RE.match(line) or ORDERED_LIST_RE.match(line)
        if m:
            # indent of the marker itself (group(1) is the whitespace before marker)
            last_indent = len(m.group(1))
        indents[idx] = last_indent
    return indents


def format_markdown(
    text: str,
    *,
    list_marker: str = "-",
    tab_width: int = 4,
    remove_trailing_space: bool = True,
    align_lists: bool = True,
    ensure_blank_before_heading: bool = True,
    normalize_blanks: bool = True,
) -> str:
    """Apply mdfmt transformations to *text* and return the formatted result."""
    lines = text.splitlines(keepends=True)

    # Pass 1: per-line cleaning (trailing space, tab expansion, list marker)
    cleaned: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.rstrip("\n\r")

        if remove_trailing_space:
            stripped = _strip_trailing(stripped)

        # Track fenced code blocks — do not reformat inside
        fence_m = FENCE_RE.match(stripped)
        if fence_m:
            in_fence = not in_fence
            _ = len(fence_m.group(1))
            cleaned.append(stripped)
            continue

        if in_fence:
            cleaned.append(stripped)
            continue

        if tab_width > 0:
            stripped = _expand_tabs(stripped, tab_width)

        stripped = _normalize_list_marker(stripped, list_marker)

        cleaned.append(stripped)

    # Recompose into lines without line endings for structural passes
    text_lines = [line.rstrip("\n\r") for line in cleaned]

    # Pass 2: structural normalization
    if ensure_blank_before_heading:
        text_lines = _ensure_blank_before_heading(text_lines)

    if normalize_blanks:
        text_lines = _normalize_blanks(text_lines)

    if align_lists:
        indents = _collect_list_indent(text_lines)
        text_lines = [
            _align_list_continuation(line, indents.get(i, 0), tab_width)
            for i, line in enumerate(text_lines)
        ]

    # Re-add newlines
    result_lines = [line + "\n" for line in text_lines]
    # Ensure file ends with exactly one newline
    if result_lines:
        result_lines[-1] = result_lines[-1].rstrip("\n") + "\n"
    else:
        result_lines = ["\n"]

    return "".join(result_lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None, stdin: Optional[str] = None) -> int:
    """Entry point for the ``mdfmt`` console script.

    Returns an exit code (0 = ok, 1 = file error, 2 = usage error).
    """
    parser = argparse.ArgumentParser(
        prog="mdfmt",
        description="Markdown formatter — normalize indentation, spacing, "
        "list markers, and blank-line consistency.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Markdown files to format. When empty, read from stdin.",
    )
    parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Write formatted output back to the input file(s).",
    )
    parser.add_argument(
        "--list-marker",
        default="-",
        choices=["-", "*", "+"],
        help="Normalize unordered list markers to this character (default: '-').",
    )
    parser.add_argument(
        "--tab-width",
        type=int,
        default=4,
        help="Expand leading tabs to this many spaces (default: 4). "
        "Set to 0 to disable tab expansion.",
    )
    parser.add_argument(
        "--no-remove-trailing-space",
        action="store_true",
        help="Preserve trailing whitespace.",
    )
    parser.add_argument(
        "--no-align-lists",
        action="store_true",
        help="Disable list continuation alignment.",
    )
    parser.add_argument(
        "--no-blank-before-heading",
        action="store_true",
        help="Disable insertion of blank lines before headings.",
    )
    parser.add_argument(
        "--no-normalize-blanks",
        action="store_true",
        help="Disable blank-line collapsing.",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    remove_trailing = not args.no_remove_trailing_space
    align_lists = not args.no_align_lists
    blank_heading = not args.no_blank_before_heading
    normalize_blanks = not args.no_normalize_blanks

    paths = args.paths

    if not paths:
        # Stdin mode
        raw_stdin: str
        if stdin is None:
            raw_stdin = sys.stdin.read()
        else:
            raw_stdin = stdin
        formatted = format_markdown(
            raw_stdin,
            list_marker=args.list_marker,
            tab_width=args.tab_width,
            remove_trailing_space=remove_trailing,
            align_lists=align_lists,
            ensure_blank_before_heading=blank_heading,
            normalize_blanks=normalize_blanks,
        )
        sys.stdout.write(formatted)
        return 0

    ret = 0
    for path in paths:
        try:
            raw = _read_file(path)
        except OSError as exc:
            print(f"mdfmt: cannot read {path}: {exc}", file=sys.stderr)
            ret = 1
            continue

        formatted = format_markdown(
            raw,
            list_marker=args.list_marker,
            tab_width=args.tab_width,
            remove_trailing_space=remove_trailing,
            align_lists=align_lists,
            ensure_blank_before_heading=blank_heading,
            normalize_blanks=normalize_blanks,
        )

        if args.in_place:
            try:
                _write_file(path, formatted)
            except OSError as exc:
                print(f"mdfmt: cannot write {path}: {exc}", file=sys.stderr)
                ret = 1
        else:
            sys.stdout.write(formatted)

    return ret


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write_file(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


if __name__ == "__main__":
    raise SystemExit(main())
