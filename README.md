# mdfmt — Markdown Formatter CLI

Normalize Markdown files from the command line — fix indentation, spacing, heading hierarchy, list alignment, and blank-line consistency. One command, zero runtime dependencies.

## Author

- **Name:** Manya chandra
- **GitHub:** https://github.com/Manyachandra
- **Email:** 132090383+Manyachandra@users.noreply.github.com

## About

Markdown is easy to write but easy to get messy: inconsistent indentation, mixed tabs and spaces, headings that skip levels, unordered lists that switch between `*`, `-`, and `+`, and erratic blank lines around blocks. `mdfmt` applies a consistent, opinionated style to any Markdown file or stream.

It is designed for editors, documentation pipelines, and pre-commit hooks — not for changing your content. It rewrites whitespace and structure, never the words.

## Features

- **Consistent unordered-list markers** — normalize all `-`, `*`, `+` to a single chosen marker
- **List indentation alignment** — align wrapped list items to the marker column
- **Blank-line normalization** — one blank line between blocks, none at EOF
- **Heading-level gap enforcement** — optional: ensure at least one blank line above headings
- **Trailing-whitespace removal** — strip trailing spaces and tabs on every line
- **Tab-to-space conversion** — expand leading tabs to spaces at a chosen width
- **Indent preservation for code fences** — do not re-indent fenced code blocks
- **In-place and stdout modes** — `-i` for files, pipe-friendly for stdin
- **Zero runtime dependencies** — stdlib only: `argparse`, `re`, `sys`

## Tech Stack

| Component | Details |
|-----------|---------|
| Language | Python 3.11+ |
| Dependencies | None (stdlib only) |
| Packaging | `pyproject.toml` with setuptools |
| Testing | `pytest` |
| Linting | `ruff` |
| Layout | Flat single-module (`mdfmt.py`) |

## Project Structure

```
mdfmt/
├── mdfmt.py           # Main module (flat single-module layout)
├── pyproject.toml     # Packaging and metadata
├── README.md          # This file
├── .gitignore
└── tests/
    └── test_mdfmt.py  # pytest suite
```

## Getting Started

### Install

```bash
pip install mdfmt
```

### Format a file (stdout)

```bash
mdfmt README.md
```

### Format in place

```bash
mdfmt -i README.md
```

### Pipe from stdin

```bash
cat draft.md | mdfmt > formatted.md
```

### Normalize list markers

```bash
mdfmt -i notes.md --list-marker "-"
```

All `*` and `+` unordered markers become `-`.

### Convert leading tabs to spaces

```bash
mdfmt -i doc.md --tab-width 4
```

### Combine flags

```bash
mdfmt -i messy.md --list-marker "-" --tab-width 2 --remove-trailing-space
```

### Show help

```bash
mdfmt --help
```

## What mdfmt does NOT do

- It does not reorder headings or fix skipped heading levels.
- It does not rewrite prose, fix spelling, or change list content.
- It does not touch HTML blocks, definition lists, or table cell alignment beyond basic trimming.
- It does not parse Markdown into a full AST; it works line-by-line with conservative context.

## Topics

`markdown`, `formatter`, `cli`, `beautifier`, `docs`, `lint`, `python`, `stdlib`, `text-processing`

## License

MIT
