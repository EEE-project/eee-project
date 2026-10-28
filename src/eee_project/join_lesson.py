"""Join the language notebooks that ``python -m eee_project.split_lesson`` made back into one multilingual notebook: notebook_ru.py, notebook_el.py, notebook_en.py -> notebook.py.
Every language text is taken from the notebook of its language.
- notebook.py exists: only the language texts in it change; every other byte stays.
- notebook.py does not exist: it is made from notebook_ru.py (the first language), with the selector call as it was before the split.
A language notebook that marimo saved since the split is fine (marimo rewrites its header and its `def _(...)` lines).

Usage: python -m eee_project.join_lesson NOTEBOOK.py [--write]
  without --write   show what would change (a diff, or the size of the new notebook) and write nothing
  --write           write NOTEBOOK.py
Refused, nothing written: a language notebook differs from NOTEBOOK.py outside the language texts (a code line, a cell), text typed into the empty place of another language,
a missing language notebook, two notebooks with different text for one place.
A text that was edited in NOTEBOOK.py after the split is replaced by the text of the language notebook: read the diff before you write."""
import argparse
import difflib
import sys
from pathlib import Path

from eee_project.lesson_languages import LANGS, MergeError, join_source, out_name, read_lf, write_lf


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebook", type=Path)
    ap.add_argument("--write", action="store_true", help="write the notebook (without it: show the diff and write nothing)")
    args = ap.parse_args()
    path, write = args.notebook.resolve(), args.write
    names = {lang: path.parent / out_name(path.name, lang) for lang in LANGS}
    missing = [p.name for p in names.values() if not p.exists()]
    if missing:
        sys.exit(f"missing language notebook(s) next to {path.name}: {', '.join(missing)}")
    original = read_lf(path) if path.exists() else None
    try:
        joined = join_source({lang: read_lf(p) for lang, p in names.items()}, original)
    except MergeError as exc:
        sys.exit(f"{path.name}: {exc}")
    if original is None:
        print(f"{path.name} does not exist: it is made from {names[LANGS[0]].name} ({joined.count(chr(10))} lines)")
    elif joined == original:
        print(f"no changes: the language notebooks hold the same texts as {path.name}")
        return
    else:
        print("\n".join(difflib.unified_diff(original.split("\n"), joined.split("\n"), f"{path.name} (now)", f"{path.name} (joined)", lineterm="", n=2)))
    if write:
        write_lf(path, joined)
        print(f"wrote {path}")
    else:
        print("nothing written: add --write to write it")


if __name__ == "__main__":
    main()
