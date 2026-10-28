"""Split a multilingual lesson notebook into one notebook per language, in the same folder: notebook.py -> notebook_ru.py, notebook_el.py, notebook_en.py, plus a README.md that lists the files of each language.

Each language notebook has the same cells in the same order. Its language selector is fixed to its language (one line, marked by a comment) and the text of the other languages is empty there.
The way back is ``python -m eee_project.join_lesson``. Details: ``eee_project.lesson_languages`` and docs/api-patterns.md ("Lesson languages").

Usage: python -m eee_project.split_lesson NOTEBOOK.py [--readme NAME]
  --readme   the name of the file list in the notebook's folder (default README.md)
An existing file is never overwritten: if one of the files exists, nothing is written. Nothing is written either unless the three notebooks join back to NOTEBOOK.py byte for byte."""
import argparse
import sys
from pathlib import Path

from eee_project.lesson_languages import LANGS, MergeError, SplitError, out_name, read_lf, readme_text, split_source, write_lf


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebook", type=Path)
    ap.add_argument("--readme", default="README.md", help="the name of the file list in the notebook's folder")
    args = ap.parse_args()
    path, readme = args.notebook.resolve(), args.readme
    src = read_lf(path)
    try:
        files, report = split_source(src)
    except (SplitError, MergeError) as exc:
        sys.exit(f"{path.name}: {exc}")
    out_names = {lang: out_name(path.name, lang) for lang in LANGS}
    targets = {out_names[lang]: files[lang] for lang in LANGS}
    targets[readme] = readme_text(path.parent, path.name, out_names, report, {readme}, src)
    exists = [name for name in targets if (path.parent / name).exists()]
    if exists:
        sys.exit(f"not overwritten, nothing written: {', '.join(exists)} exist(s) in {path.parent}")
    for name, text in targets.items():
        write_lf(path.parent / name, text)
        print(f"wrote {path.parent / name}")
    print(f"{report['dict entries']} dict values and {report['chains']} if-chains split; left as they are: " + (", ".join(f"{k} {v}" for k, v in report["left as they are"].items() if v) or "nothing"))
    for lineno, why in report["unsupported"]:
        print(f"  not split, line {lineno}: {why}")


if __name__ == "__main__":
    main()
