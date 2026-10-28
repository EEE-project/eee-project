"""One notebook per language: split a multilingual lesson notebook into notebook_ru.py, notebook_el.py and notebook_en.py, and join them back.
Commands: ``python -m eee_project.split_lesson NOTEBOOK.py`` and ``python -m eee_project.join_lesson NOTEBOOK.py [--write]``.

Each language notebook has the same cells in the same order. Its language selector is fixed to its language (one line, marked by a comment). The text of a language stays only in the notebook of that language:
  - the values of a dict whose keys are language codes ({"ru": ..., "el": ..., "en": ...}): the other languages' values become empty placeholders ("", (), [], {}, None); the keys stay;
  - the bodies of an if/elif/else chain on the language (if _lang == "ru": ... elif _lang == "el": ... else: ...): the other branches become `pass`.
Every key and every branch still exists, so code like `_TXT.get(lang, _TXT["ru"])` still runs. Nothing else changes.
Left as they are (named in the report): conditional expressions on the language, other ifs on the language, dicts with other keys.

`split_source(src)` returns the notebooks and refuses unless `join_source(files) == src` byte for byte.
`join_source(files, original=None)` is the way back: every text comes from the notebook of its language. With the original notebook only the language texts in it change and every other byte stays.
A notebook that marimo saved since the split is fine: marimo rewrites its header and its `def _(...)` lines, and they are not compared.
Needs only the standard library, `git` (for the file list of the README) and `eee_project.content` (the labels of the language dropdown)."""
import ast
import functools
import re
import subprocess
from dataclasses import dataclass

from eee_project.content import _LANGUAGE_OPTIONS

LANGS = ("ru", "el", "en")
SUBJECTS = ("_lang",)
LABELS = {code: label for label, code in _LANGUAGE_OPTIONS.items()}   # the labels of language_selector's dropdown, {code: label}
NAMES = {"ru": "Russian", "el": "Greek", "en": "English"}
MARK = re.compile(r"  # eee-split lang=(?P<lang>\w+) orig=(?P<orig>.*)$")


class SplitError(Exception):
    pass


class MergeError(Exception):
    pass


@dataclass(frozen=True)
class Slot:
    start: int            # character offsets in the source
    end: int
    owners: tuple         # the languages whose file keeps the text
    fill: str             # what the files of the other languages hold there
    kind: str             # "dict" or "chain"


def layout(src):
    lines = src.split("\n")
    starts, pos = [], 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln) + 1
    return lines, starts


@functools.lru_cache(maxsize=8)
def parse(src):
    """ast.parse with a small cache: a join reads each text several times (the syntax check, find, canonical)."""
    return ast.parse(src)


def char_col(line, byte_col):
    """The character column of a UTF-8 byte column (ast counts bytes)."""
    return len(line.encode("utf-8")[:byte_col].decode("utf-8"))


def pos_of(lines, starts, lineno, byte_col):
    return starts[lineno - 1] + char_col(lines[lineno - 1], byte_col)


def splice(text, edits):
    """`text` with every (start, end, new) range replaced; the ranges must not overlap."""
    out, pos = [], 0
    for start, end, new in sorted(edits, key=lambda e: e[0]):
        assert start >= pos, "two edits overlap"
        out.append(text[pos:start])
        out.append(new)
        pos = end
    out.append(text[pos:])
    return "".join(out)


def test_lang(test):
    """The language code of `<subject> == "<code>"`, else None."""
    if (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) and ast.unparse(test.left) in SUBJECTS
            and isinstance(test.comparators[0], ast.Constant) and isinstance(test.comparators[0].value, str)):
        return test.comparators[0].value
    return None


BLANKS = {"pass", '""', "''", 'b""', "b''", "False", "0", "0.0", "None", "()", "[]", "{}", "set()"}   # what placeholder() writes (and a formatter's single-quote spelling)


def placeholder(value):
    if isinstance(value, ast.Constant):
        return {str: '""', bytes: 'b""', bool: "False", int: "0", float: "0.0", type(None): "None"}.get(type(value.value), "None")
    return {ast.JoinedStr: '""', ast.Tuple: "()", ast.List: "[]", ast.Dict: "{}", ast.Set: "set()"}.get(type(value), "None")


def chain_slots(node, elifs, lines, starts):
    """(slots, None) for the if/elif/else chain on the language that starts at `node`: one slot for the body of each branch; (None, why) when the chain cannot be split."""
    chain, cur, tested = [], node, []
    while True:
        code = test_lang(cur.test)
        if code is None or code not in LANGS or code in tested:
            return None, "an elif test is not a new language code on the same variable"
        tested.append(code)
        chain.append(((code,), cur.body))
        if len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If) and id(cur.orelse[0]) in elifs:
            cur = cur.orelse[0]
            continue
        break
    rest = tuple(c for c in LANGS if c not in tested)
    if cur.orelse:
        if not rest:
            return None, "the else can never run (all language codes are tested)"
        chain.append((rest, cur.orelse))
    slots = []
    for owners, body in chain:
        first, last = body[0], body[-1]
        indent = lines[first.lineno - 1][:first.col_offset]
        tail = lines[last.end_lineno - 1][char_col(lines[last.end_lineno - 1], last.end_col_offset):]
        if indent.strip() or "\t" in indent or (tail.strip() and not tail.lstrip().startswith("#")):
            return None, "a branch is not made of whole lines (one-line body, tab or a second statement on a line)"
        slots.append(Slot(starts[first.lineno - 1], starts[last.end_lineno - 1] + len(lines[last.end_lineno - 1]), owners, indent + "pass", "chain"))
    return slots, None


def find(src):
    """(slots, pin, report) of a source: the places whose text belongs to one language, the selector call, and what was left as it is."""
    tree = parse(src)
    lines, starts = layout(src)

    def begin(n):
        return pos_of(lines, starts, n.lineno, n.col_offset)

    def finish(n):
        return pos_of(lines, starts, n.end_lineno, n.end_col_offset)

    frags, notes = [], []
    # shortcut: ternaries and other ifs on the language are only counted (the fixed selector makes them run in one language), split them when a text sits in one
    left = {"ternary on the language": 0, "other if on the language": 0, "dict with other keys": 0}
    elifs = {id(n.orelse[0]) for n in ast.walk(tree) if isinstance(n, ast.If) and len(n.orelse) == 1 and isinstance(n.orelse[0], ast.If)
             and lines[n.orelse[0].lineno - 1].lstrip().startswith("elif")}
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict) and node.keys and all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in node.keys):
            keys = [k.value for k in node.keys]
            if len(set(keys)) == len(keys) and len(keys) >= 2 and set(keys) <= set(LANGS):
                frags.append((begin(node), finish(node), [Slot(begin(v), finish(v), (k,), placeholder(v), "dict") for k, v in zip(keys, node.values)]))
            elif len(set(keys) & set(LANGS)) >= 2:
                left["dict with other keys"] += 1
        elif isinstance(node, ast.If) and id(node) not in elifs and test_lang(node.test) is not None:
            branches, why = chain_slots(node, elifs, lines, starts)
            if branches is None:
                notes.append((node.lineno, why))
            else:
                frags.append((begin(node), finish(node), branches))
        elif isinstance(node, ast.IfExp) and any(test_lang(c) or (isinstance(c, ast.Constant) and c.value in LANGS) for c in ast.walk(node.test)):
            left["ternary on the language"] += 1
        elif isinstance(node, ast.If) and id(node) not in elifs and any(isinstance(c, ast.Constant) and c.value in LANGS for c in ast.walk(node.test)):
            left["other if on the language"] += 1
    frags.sort(key=lambda f: (f[0], -f[1]))
    kept, edge = [], -1
    for start, end, slots in frags:          # an inner fragment (inside the text of an outer one) stays as it is
        if start >= edge:
            kept.append(slots)
            edge = end
    slots = sorted((s for group in kept for s in group), key=lambda s: s.start)
    for a, b in zip(slots, slots[1:]):
        assert a.end <= b.start, (a, b)
    pins = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ((isinstance(n.func, ast.Name) and n.func.id == "language_selector")
                                                                  or (isinstance(n.func, ast.Attribute) and n.func.attr == "language_selector"))]
    pin = None
    if len(pins) == 1:
        call = pins[0]
        line = lines[call.lineno - 1]
        c0, c1 = begin(call), finish(call)
        end_of_line = starts[call.end_lineno - 1] + len(lines[call.end_lineno - 1])
        mark = MARK.search(lines[call.end_lineno - 1])
        pin = {"start": c0, "end": c1, "eol": end_of_line, "text": src[c0:c1], "single_line": call.lineno == call.end_lineno,
               "plain": len(call.args) == 2 and not call.keywords and src[c1:end_of_line] == "", "marked": mark, "lineno": call.lineno, "has_comment": "#" in line[char_col(line, call.col_offset):]}
    report = {"chains": sum(1 for group in kept if group[0].kind == "chain"), "dict entries": sum(1 for s in slots if s.kind == "dict"),
              "selector calls": len(pins), "unsupported": notes, "left as they are": left}
    return slots, pin, report


def pin_text(pin, lang):
    label = LABELS.get(lang, lang)
    call = pin["text"][:-1] + f', options={{"{label}": "{lang}"}}, default="{lang}")'
    return call + f"  # eee-split lang={lang} orig={pin['text']}"


def render(src, slots, pin, lang):
    return splice(src, [(s.start, s.end, s.fill) for s in slots if lang not in s.owners] + [(pin["start"], pin["eol"], pin_text(pin, lang))])


def split_source(src):
    """{lang: text} for every language, and the report. Raises SplitError when the notebook cannot be split safely."""
    if "\r" in src or "\x00" in src or "\x01" in src:
        raise SplitError("the source holds a CR, NUL or SOH character: convert it to LF line ends first")
    slots, sel, report = find(src)
    # shortcut: only `language_selector(a, b)` is fixed; ellinika_b, Kavafis, Zorba and Kapodistrias get the selector from a cell parameter and are refused, add their rule when they are in scope
    if not sel:
        raise SplitError(f"expected one language_selector(...) call to fix, found {report['selector calls']}")
    if not (sel["plain"] and sel["single_line"]) or sel["marked"] or sel["has_comment"]:
        raise SplitError(f"the language_selector call at line {sel['lineno']} must be `language_selector(a, b)` alone at the end of one line, without a comment, and not yet split")
    if not slots:
        raise SplitError("nothing to split: no dict keyed by language codes and no if-chain on the language")
    files = {lang: render(src, slots, sel, lang) for lang in LANGS}
    back = join_source(files)
    if back != src:
        at = next((i for i, (a, b) in enumerate(zip(back, src)) if a != b), min(len(back), len(src)))
        raise SplitError(f"the round trip is not exact (first difference near character {at}): nothing written")
    return files, report


def read_markers(files):
    """The selector call that the split replaced, read from the markers of language notebooks made by one split; MergeError when they were not."""
    if not files:
        raise MergeError("no language notebooks given")
    origs = set()
    for lang, text in files.items():
        marks = [m for ln in text.split("\n") for m in [MARK.search(ln)] if m]
        if len(marks) != 1:
            raise MergeError(f"{lang}: expected one `# eee-split` marker, found {len(marks)}")
        if marks[0].group("lang") != lang:
            raise MergeError(f"the file given as {lang} says lang={marks[0].group('lang')}")
        origs.add(marks[0].group("orig"))
    if len(origs) != 1:
        raise MergeError("the files were not made by one split (the markers differ)")
    if set(files) != set(LANGS):
        raise MergeError(f"the files are for {sorted(files)}, the split was for {sorted(LANGS)}")
    return origs.pop()


def tokenize(text, slots, pin):
    """The text with each language text replaced by NUL and the selector line, from the call to its end, by SOH."""
    return splice(text, [(s.start, s.end, "\x00") for s in slots] + [(pin["start"], pin["eol"], "\x01")])


def first_difference(a, b):
    """'line N: <line of b> instead of <line of a>' for the first line where two texts differ."""
    x, y = a.split("\n"), b.split("\n")
    k = next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
    return f"line {k + 1}: {y[k][:80] if k < len(y) else '(end)'!r} instead of {x[k][:80] if k < len(x) else '(end)'!r}"


def canonical(text):
    """For comparing only: the text without what a marimo save rewrites. That is the value of `__generated_with`, the layout of `app = marimo.App(...)`,
    and the `def` line(s) of every cell and its final `return` with the blank lines above it (marimo derives both from the names the cell uses; a cell that holds only a `return` becomes `pass`)."""
    lines = text.split("\n")
    edits = []      # (first line, last line, new lines), counted from 0
    for node in parse(text).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ("__generated_with", "app") for t in node.targets):
            is_app = any(isinstance(t, ast.Name) and t.id == "app" for t in node.targets)
            edits.append((node.lineno - 1, node.end_lineno - 1, [ast.unparse(node) if is_app else "__generated_with = ''"]))
        elif isinstance(node, ast.FunctionDef) and any(ast.unparse(d).startswith("app.cell") for d in node.decorator_list):
            last = node.lineno - 1
            while not lines[last].rstrip().endswith(":"):
                last += 1
            edits.append((node.lineno - 1, last, [f"def {node.name}():"]))
            if isinstance(node.body[-1], ast.Return):
                ret = node.body[-1]
                first = ret.lineno - 1
                while first - 1 > last and not lines[first - 1].strip():     # marimo puts a blank line above the return in some cells
                    first -= 1
                edits.append((first, ret.end_lineno - 1, [" " * ret.col_offset + "pass"] if len(node.body) == 1 else []))
    for first, last, new in sorted(edits, reverse=True):
        lines[first:last + 1] = new
    return "\n".join(lines)


def join_source(files, original=None):
    """The multilingual notebook from the language notebooks {lang: text}: every language text is taken from the notebook of its language.
    Without `original` the first language notebook is the base (the selector call comes back from its marker): for notebooks as split_source made them the result is the source, byte for byte.
    With `original` (the multilingual notebook as it is now) the result is `original` with only the language texts replaced; every other byte stays.
    A language notebook that marimo saved since the split is fine: its header and its `def _(...)` / `return` lines are not compared.
    MergeError when a notebook differs from the base outside the language texts, holds text in the empty place of another language, or two notebooks hold different text for one place."""
    if "\r" in (original or "") or any("\r" in text for text in files.values()):
        raise MergeError("a CR character in a notebook: convert the line ends to LF first")
    for label, text in [(f"the {lang} notebook", t) for lang, t in files.items()] + ([("the original", original)] if original is not None else []):
        try:
            parse(text)
        except SyntaxError as exc:
            raise MergeError(f"{label} does not parse (line {exc.lineno}: {exc.msg})") from None
    orig_call = read_markers(files)
    base = files[LANGS[0]] if original is None else original
    name = f"the {LANGS[0]} notebook" if original is None else "the original"
    slots, pin, _ = find(base)
    if original is not None and (not pin or pin["marked"] or pin["text"] != orig_call):
        raise MergeError(f"the original must hold the call {orig_call!r} once, as before the split; found {pin['text'] if pin else 'no call'!r}")
    if not pin:
        raise MergeError(f"{LANGS[0]}: the marked selector line was not found")
    c_base = canonical(base)
    c_slots, c_pin, _ = find(c_base)
    skeleton = tokenize(c_base, c_slots, c_pin)
    texts = [{} for _ in slots]
    for lang, text in files.items():
        l_slots, l_pin, _ = find(text)
        if not l_pin or not l_pin["marked"]:
            raise MergeError(f"{lang}: the marked selector line was not found")
        c_text = canonical(text)
        c_l_slots, c_l_pin, _ = find(c_text)
        mine = tokenize(c_text, c_l_slots, c_l_pin)
        if mine != skeleton:
            raise MergeError(f"outside the language texts, the {lang} notebook differs from {name} at {first_difference(skeleton, mine)}")
        # no input reaches this while canonical() keeps the keys and tests of the places; kept so a change of canonical() cannot silently drop a text
        if [s.owners for s in l_slots] != [s.owners for s in slots]:
            raise MergeError(f"{lang}: the language texts are not in the same places as in {name}")
        for i, (s, o) in enumerate(zip(l_slots, slots)):
            if lang in o.owners:
                texts[i][lang] = text[s.start:s.end]
            elif text[s.start:s.end].strip() not in BLANKS:     # text typed into the empty place of another language would be lost
                raise MergeError(f"{lang}: language text {i + 1} belongs to {'/'.join(o.owners)}, but the {lang} notebook holds text there; edit it in the notebook of its language")
    # shortcut: a text edited in the original after the split is overwritten by the language notebook's text (the dry run shows it); keep a hash of the source in the marker if that loses work
    # shortcut: with an original the `def _(...)` lines stay as they are; a new name that an edit brings into a cell is added by marimo at its next save (not checked)
    edits = []
    for i, o in enumerate(slots):
        if len(set(texts[i].values())) != 1:
            raise MergeError(f"conflict at language text {i + 1} ({o.kind}): the notebooks {sorted(texts[i])} hold different text")
        edits.append((o.start, o.end, next(iter(texts[i].values()))))
    if original is None:
        edits.append((pin["start"], pin["eol"], orig_call))
    return splice(base, edits)


def out_name(name, lang):
    """notebook.py -> notebook_ru.py; notebook.26_05_22.py -> notebook_ru.26_05_22.py (the language label after the first name part)."""
    stem, dot, rest = name.partition(".")
    return f"{stem}_{lang}{dot}{rest}"


def git_names(where):
    """The names of the files directly in `where` that git tracks or would add (not ignored); None outside a git repository."""
    try:
        done = subprocess.run(["git", "-C", str(where), "ls-files", "-z", "--cached", "--others", "--exclude-standard"], capture_output=True, text=True)
    except OSError:
        return None
    return {name for name in done.stdout.split("\0") if name and "/" not in name} if done.returncode == 0 else None


def language_files(folder, skip):
    """({lang: [names]}, [shared names], unlabeled): the files of the folder and of the course folder above that carry a language label (name_ru.ext), and the files of the folder that do not.
    A file without a label belongs to the one language that has no labeled file of that name (vocab.tsv next to vocab_el.tsv and vocab_en.tsv is Russian); `unlabeled` says that this happened."""
    groups, shared, unlabeled = {lang: [] for lang in LANGS}, [], False
    for where, prefix in ((folder, ""), (folder.parent, "../")):
        keep = git_names(where)     # a downloaded, git-ignored file would make the list differ from machine to machine
        names = sorted(p.name for p in where.iterdir() if p.is_file() and not p.name.startswith(".") and (keep is None or p.name in keep))
        labeled = {}
        for name in names:
            stem, dot, ext = name.rpartition(".")
            m = re.fullmatch(r"(.+)_(" + "|".join(LANGS) + r")", stem) if dot else None
            if m:
                labeled.setdefault((m.group(1), ext), {})[m.group(2)] = name
        owned = set()
        for (stem, ext), by_lang in labeled.items():
            missing = [lang for lang in LANGS if lang not in by_lang]
            for lang, name in by_lang.items():
                groups[lang].append(prefix + name)
                owned.add(name)
            if len(missing) == 1 and f"{stem}.{ext}" in names:
                groups[missing[0]].append(prefix + f"{stem}.{ext}")
                owned.add(f"{stem}.{ext}")
                unlabeled = True
        if where is folder:
            shared = [n for n in names if n not in owned and n not in skip]
    return groups, shared, unlabeled


def readme_text(folder, source_name, out_names, report, skip, src):
    """The file list: one row per language, then the files that all languages share. `out_names` {lang: notebook name} are not on disk yet."""
    groups, shared, has_unlabeled = language_files(folder, set(skip) | set(out_names.values()) | {source_name})

    def code(names):
        return ", ".join(f"`{n}`" for n in names) or "-"

    unlabeled = "A file without a language label belongs to the language that has no labeled file of the same name.\n" if has_unlabeled else ""
    downloads = "The translation texts (`translations_<language>.md`) are downloaded from the knowledge base when a notebook runs. Git ignores them.\n" if "translations_" in src else ""
    rows = "\n".join(f"| {NAMES.get(lang, lang)} (`{lang}`) | `{out_names[lang]}` | {code(n for n in groups[lang] if n not in out_names.values())} |" for lang in LANGS)
    return f"""# Language files of this folder

`{source_name}` is the source notebook: it holds the text of all languages and a language selector.
`python -m eee_project.split_lesson` made one notebook for each language from it. A language notebook has the same cells in the same order.
It differs from the source in the language selector (fixed to one language), {report['dict entries']} dict values and {report['chains']} if-chains: the text of the other languages is empty there.

## Files by language

| Language | Notebook | Other files of this language |
|:--|:--|:--|
{rows}

{unlabeled}The list shows the files that were in the folder when the notebooks were made, without the files that git ignores.
{downloads}
## Files for all languages

{code([source_name] + shared)}

## Rules

- In a language notebook, change only the text of its language.
- To bring the changed texts back into `{source_name}`: run `python -m eee_project.join_lesson {source_name}` (it shows what would change), then `python -m eee_project.join_lesson {source_name} --write`.
- To change any other line: (1) join as above; (2) change `{source_name}`; (3) delete the language notebooks and make them again.
"""


def read_lf(path):
    with open(path, encoding="utf-8", newline="") as f:   # newline="": a CR stays visible, so split_source can refuse it
        return f.read()


def write_lf(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:   # newline="": LF stays LF
        f.write(text)
