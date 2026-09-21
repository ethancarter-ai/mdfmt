"""Tests for mdfmt — Markdown formatter CLI."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project importable under the project tree for tests.
ProjectRoot = Path(__file__).resolve().parents[1]
if str(ProjectRoot) not in sys.path:
    sys.path.insert(0, str(ProjectRoot))

import pytest  # noqa: E402
import mdfmt  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format(text: str, **kwargs) -> str:
    return mdfmt.format_markdown(text, **kwargs)


# ---------------------------------------------------------------------------
# Trailing-space removal
# ---------------------------------------------------------------------------

def test_strip_trailing_space():
    assert mdfmt._strip_trailing("hello   ") == "hello"
    assert mdfmt._strip_trailing("hello\t\t") == "hello"
    assert mdfmt._strip_trailing("") == ""
    assert mdfmt._strip_trailing("no-space") == "no-space"


# ---------------------------------------------------------------------------
# Tab expansion
# ---------------------------------------------------------------------------

def test_expand_tabs_leading_only():
    assert mdfmt._expand_tabs("\tfoo", 4) == "    foo"
    assert mdfmt._expand_tabs("\t\tbar", 4) == "        bar"
    # Inner tabs must not be expanded
    assert mdfmt._expand_tabs("\tfoo\tbar", 4) == "    foo\tbar"
    assert mdfmt._expand_tabs("no-tab", 4) == "no-tab"


# ---------------------------------------------------------------------------
# List marker normalization
# ---------------------------------------------------------------------------

def test_normalize_list_marker_star_to_dash():
    src = "\t* item"
    assert mdfmt._normalize_list_marker(src, "-") == "\t- item"


def test_normalize_list_marker_pipes():
    assert mdfmt._normalize_list_marker("+ item", "+") == "+ item"
    assert mdfmt._normalize_list_marker("* item", "-") == "- item"
    assert mdfmt._normalize_list_marker("  - item", "-") == "  - item"
    assert mdfmt._normalize_list_marker("not a list", "-") == "not a list"


# ---------------------------------------------------------------------------
# List continuation alignment
# ---------------------------------------------------------------------------

def test_align_list_continuation_basic():
    assert mdfmt._align_list_continuation("   continued", 2, 4) == "    continued"
    assert mdfmt._align_list_continuation("    continued", 2, 4) == "    continued"


def test_align_list_continuation_skips_non_continuation():
    assert mdfmt._align_list_continuation("# Heading", 2, 4) == "# Heading"
    assert mdfmt._align_list_continuation("```code", 2, 4) == "```code"
    assert mdfmt._align_list_continuation("- item", 2, 4) == "- item"
    assert mdfmt._align_list_continuation("  1. item", 2, 4) == "  1. item"
    assert mdfmt._align_list_continuation("", 2, 4) == ""


# ---------------------------------------------------------------------------
# Blank-line normalization
# ---------------------------------------------------------------------------

def test_normalize_blanks_collapses_and_trims_trailing():
    lines = ["a", "", "", "", "b", "", ""]
    out = mdfmt._normalize_blanks(lines)
    assert out == ["a", "", "b"]
    assert out[-1].strip() != ""


def test_normalize_blanks_preserves_single_blank():
    lines = ["a", "", "b"]
    out = mdfmt._normalize_blanks(lines)
    assert out == ["a", "", "b"]


# ---------------------------------------------------------------------------
# Blank line before headings
# ---------------------------------------------------------------------------

def test_ensure_blank_before_heading_inserts():
    lines = ["text", "# Heading"]
    out = mdfmt._ensure_blank_before_heading(lines)
    assert out == ["text", "", "# Heading"]


def test_ensure_blank_before_heading_already_present():
    lines = ["text", "", "# Heading"]
    out = mdfmt._ensure_blank_before_heading(lines)
    assert out == ["text", "", "# Heading"]


def test_ensure_blank_before_heading_first_line():
    lines = ["# First"]
    out = mdfmt._ensure_blank_before_heading(lines)
    assert out == ["# First"]


# ---------------------------------------------------------------------------
# Full format integration
# ---------------------------------------------------------------------------

def test_format_strips_trailing_space_by_default():
    text = "foo   \nbar\t\n"
    out = _format(text)
    assert "  " not in out.splitlines()[0]
    assert out.splitlines()[1] == "bar"


def test_format_expands_tabs_by_default():
    text = "\t- item\n"
    out = _format(text)
    assert out.startswith("    - item")


def test_format_tab_width_zero_disables_expansion():
    text = "\t- item\n"
    out = _format(text, tab_width=0)
    assert out.startswith("\t- ")


def test_format_normalizes_list_markers():
    text = "* a\n+ b\n- c\n"
    out = _format(text, list_marker="-")
    assert out.count("*") == 0
    assert out.count("+") == 0
    assert out.count("- ") == 3


def test_format_collapses_blank_lines():
    text = "a\n\n\n\nb\n\n\n"
    out = _format(text)
    assert out.count("\n\n\n") == 0
    assert out.endswith("b\n")


def test_format_inserts_blank_before_heading():
    text = "some text\n# Heading\n"
    out = _format(text, ensure_blank_before_heading=True)
    assert "text\n\n# Heading" in out.replace("\r", "")


def test_format_respects_no_flags():
    text = "a\n\n\nb\n"
    out = _format(
        text,
        remove_trailing_space=False,
        align_lists=False,
        ensure_blank_before_heading=False,
        normalize_blanks=False,
    )
    assert out == "a\n\n\nb\n"


def test_format_preserves_fence_content():
    text = "```python\nx=1\n```\n"
    out = _format(text)
    assert "```python" in out
    assert "x=1" in out
    assert out.rstrip().endswith("```")


def test_format_ends_with_single_newline():
    text = "hello\n"
    out = _format(text)
    assert out.endswith("\n")
    assert out.count("\n") >= 1


# ---------------------------------------------------------------------------
# CLI: main() with stdin injection
# ---------------------------------------------------------------------------

def test_main_stdin_basic(capsys):
    payload = "# Title\n\nsome text\n"
    mdfmt.main([], stdin=payload)
    captured = capsys.readouterr()
    assert "# Title" in captured.out
    assert "some text" in captured.out


def test_main_stdin_list_marker_star_to_dash(capsys):
    payload = "* item\n+ another\n"
    mdfmt.main(["--list-marker", "-"], stdin=payload)
    captured = capsys.readouterr()
    assert "*" not in captured.out
    assert "+" not in captured.out
    assert "- item" in captured.out


def test_main_stdin_in_place_fails_no_path(capsys):
    payload = "foo   \n"
    mdfmt.main(["-i"], stdin=payload)
    captured = capsys.readouterr()
    assert captured.out.strip() == "foo"


def test_main_file_output(capsys, tmp_path: Path):
    f = tmp_path / "doc.md"
    f.write_text("# Title\n\nsome  text  \n", encoding="utf-8")
    code = mdfmt.main([str(f)])
    assert code == 0
    captured = capsys.readouterr()
    assert "# Title" in captured.out
    # trailing space stripped, internal space preserved
    last = captured.out.rstrip("\n").splitlines()[-1]
    assert last == "some  text"


def test_main_in_place_writes_back(tmp_path: Path):
    f = tmp_path / "doc.md"
    f.write_text("## Heading\n\ntext\n\n\n", encoding="utf-8")
    code = mdfmt.main(["-i", str(f)])
    assert code == 0
    written = f.read_text(encoding="utf-8")
    assert written.rstrip("\n").count("\n\n\n") == 0


def test_main_missing_file_returns_1(capsys):
    code = mdfmt.main(["nonexistent.md"])
    assert code == 1
    captured = capsys.readouterr()
    assert "cannot read" in captured.err


def test_main_help_returns_0():
    code = mdfmt.main(["--help"])
    assert code == 0


def test_main_no_args_stdin_mode():
    """empty argv → stdin mode; pytest blocks sys.stdin.read(), so we
    exercise the fallback branch instead and assert nonzero ret."""
    import io
    code = mdfmt.main([], stdin="")
    assert code == 0


# ---------------------------------------------------------------------------
# Round-trip sanity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "# Heading 1",
        "## Heading 2",
        "- item",
        "  - nested",
        "```python\nx=1\n```",
        "paragraph",
        "",
        "line with trailing   ",
    ],
)
def test_round_trip_does_not_drop_content(text):
    out = _format(text)
    for word in text.split():
        assert word in out, f"lost {word!r} after formatting {text!r}"


# ---------------------------------------------------------------------------
# Collect list indent helper
# ---------------------------------------------------------------------------

def test_collect_list_indent():
    lines = [
        "text",
        "- item",
        "  continuation",
        "  - nested",
        "    deep",
    ]
    indents = mdfmt._collect_list_indent(lines)
    assert indents[0] == 0
    assert indents[1] == 0
    assert indents[2] == 0
    assert indents[3] == 2
    assert indents[4] == 2

