#!/usr/bin/env python3
"""Wrap a `marimo export html-wasm` output in the shared deploy-shell template.

`marimo export html-wasm <nb> -o <dist-dir>` writes one self-contained
index.html with the notebook embedded directly. The live demos instead need
a two-file structure: a lightweight shell (loading animation, topbar with a
back-link and GA, source footer, error/retry state) that iframes the actual
notebook -- so every demo shares one consistent look regardless of which
notebook it wraps. This script performs that split: the export's own
index.html becomes notebook.html, and shell_template.html (with {{TITLE}}
filled in) becomes the new index.html.

Usage:
    python3 deploy/build_shell.py <dist-dir> "<Title Text>"

Example:
    python3 deploy/build_shell.py dist/drill "Paradigm Drill"

Run after `marimo export html-wasm`, from within examples/ (see the
Makefile's export-* targets, which chain both steps together).
"""
import sys
from pathlib import Path


def build_shell(dist_dir: Path, title: str) -> None:
    """Split dist_dir's raw marimo export into shell (index.html) + app (notebook.html).

    Raises FileNotFoundError if dist_dir/index.html (the marimo export's own
    output) doesn't exist yet.
    """
    exported = dist_dir / "index.html"
    notebook = dist_dir / "notebook.html"
    if not exported.exists():
        raise FileNotFoundError(f"{exported} not found -- run the marimo export first")
    exported.rename(notebook)

    template_path = Path(__file__).parent / "shell_template.html"
    shell = template_path.read_text(encoding="utf-8").replace("{{TITLE}}", title)
    (dist_dir / "index.html").write_text(shell, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(1)

    dist_dir = Path(sys.argv[1])
    title = sys.argv[2]
    try:
        build_shell(dist_dir, title)
    except FileNotFoundError as e:
        raise SystemExit(str(e)) from e

    print(f"Wrote {dist_dir / 'index.html'} (shell) + {dist_dir / 'notebook.html'} (app)")


if __name__ == "__main__":
    main()
