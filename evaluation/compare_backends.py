#!/usr/bin/env python3
"""
One-time evaluation: compare UniMorphBackend vs dedicated backends for MG and AG.

Requires unimorph_inflect installed with model weights:
    uv run --extra unimorph python -c "import unimorph_inflect; unimorph_inflect.download('ell')"
    uv run --extra unimorph python -c "import unimorph_inflect; unimorph_inflect.download('grc')"

Run:
    uv run --extra unimorph python evaluation/compare_backends.py

Output:
    evaluation/unimorph-vs-dedicated.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import eee
from eee.backends.unimorph import UniMorphBackend

# Dedicated backends: "el" (MG) is built-in; "grc" loaded via entry point if installed
eee.register_default_backends()

unimorph = UniMorphBackend()

# ── Wordlists ─────────────────────────────────────────────────────────────────

MG_VERBS = [
    "λύω", "γράφω", "βλέπω", "λέω", "έχω",
    "κάνω", "πάω", "μένω", "δίνω", "παίρνω",
    "φεύγω", "βρίσκω", "μαθαίνω", "μιλάω", "αγοράζω",
    "διαβάζω", "ακούω", "βοηθάω", "ξέρω", "πίνω",
]

MG_NOUNS = [
    "λόγος", "άνθρωπος", "χρόνος", "τόπος", "δρόμος",
    "γυναίκα", "χώρα", "δουλειά", "ζωή", "στιγμή",
    "παιδί", "σπίτι", "βιβλίο", "χέρι", "μάτι",
    "πόλη", "φίλος", "μέρα", "νύχτα", "καρδιά",
]

AG_NOUNS = [
    "θάλαττα", "ἡμέρα", "ψυχή", "ἀρχή", "τιμή",
    "λόγος", "ἄνθρωπος", "πόλεμος", "νόμος", "στρατηγός",
]

AG_ADJ = [
    "ἀγαθός", "κακός", "καλός", "σοφός", "δίκαιος",
    "ἄξιος", "ἐλεύθερος", "δεινός", "νέος", "μόνος",
]

# ── Inflection slots ──────────────────────────────────────────────────────────

VERB_SLOTS_PRES = [
    {"Tense": "Pres", "Mood": "Ind", "Voice": "Act", "Person": p, "Number": n}
    for p in ("1", "2", "3") for n in ("Sing", "Plur")
]

VERB_SLOTS_PAST = [
    {"Tense": "Past", "Aspect": "Imp", "Mood": "Ind", "Voice": "Act", "Person": p, "Number": n}
    for p, n in [("1", "Sing"), ("3", "Sing"), ("3", "Plur")]
]

VERB_SLOTS = VERB_SLOTS_PRES + VERB_SLOTS_PAST

NOUN_SLOTS_MG = [
    {"Case": c, "Number": n}
    for c in ("Nom", "Gen", "Acc") for n in ("Sing", "Plur")
]

NOUN_SLOTS_AG = [
    {"Case": c, "Number": n}
    for c in ("Nom", "Gen", "Acc", "Dat", "Voc") for n in ("Sing", "Plur")
]

ADJ_SLOTS_AG = [
    {"Case": c, "Number": n, "Gender": g}
    for c in ("Nom", "Gen", "Acc") for n in ("Sing", "Plur") for g in ("Masc", "Fem", "Neut")
]


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_category(
    lemmas: list[str],
    slots: list[dict],
    unimorph_lang: str,
    dedicated_lang: str,
    pos: str,
    category_name: str,
) -> tuple[str, int, int, float]:
    total = 0
    agreed = 0
    errors = 0
    for lemma in lemmas:
        for features in slots:
            try:
                expected = eee.inflect(lemma, features, pos, language=dedicated_lang)
                um_forms = unimorph.inflect(lemma, features, pos, language=unimorph_lang)
                total += 1
                if expected & um_forms:
                    agreed += 1
            except Exception:
                errors += 1
    rate = agreed / total if total > 0 else 0.0
    suffix = f" ({errors} errors skipped)" if errors else ""
    print(f"{category_name}: {agreed}/{total} = {rate:.1%}{suffix}")
    return category_name, agreed, total, rate


def main() -> None:
    results = []
    results.append(evaluate_category(MG_VERBS, VERB_SLOTS,    "ell", "el",  "verb",      "MG verbs"))
    results.append(evaluate_category(MG_NOUNS, NOUN_SLOTS_MG, "ell", "el",  "noun",      "MG nouns"))
    results.append(evaluate_category(AG_NOUNS, NOUN_SLOTS_AG, "grc", "grc", "noun",      "AG nouns"))
    results.append(evaluate_category(AG_ADJ,   ADJ_SLOTS_AG,  "grc", "grc", "adjective", "AG adjectives"))

    out = Path(__file__).parent / "unimorph-vs-dedicated.md"
    with out.open("w") as f:
        f.write("# UniMorph vs Dedicated Backend Evaluation\n\n")
        f.write("| Category | Agreed | Total | Agreement Rate |\n")
        f.write("|----------|--------|-------|----------------|\n")
        for name, agreed, total, rate in results:
            f.write(f"| {name} | {agreed} | {total} | {rate:.1%} |\n")
        f.write("\n")
        f.write("_After reviewing, update `accuracy_pct` in `eee/data/languages.yaml` manually._\n")

    print(f"\nReport written to {out}")


if __name__ == "__main__":
    main()
