"""Human-readable formatting of UD FEATS grammar strings.

Independent of any UI framework or target language — usable in notebooks,
CLIs, tests, and web APIs.
"""
from __future__ import annotations

_FMT_CASE = {
    "ru": {"Nom": "Им.", "Gen": "Род.", "Dat": "Дат.", "Acc": "Вин.", "Voc": "Зват."},
    "en": {"Nom": "Nom.", "Gen": "Gen.", "Dat": "Dat.", "Acc": "Acc.", "Voc": "Voc."},
    "el": {"Nom": "Ον.", "Gen": "Γεν.", "Dat": "Δοτ.", "Acc": "Αιτ.", "Voc": "Κλ."},
}
_FMT_NUM = {
    "ru": {"Sing": "ед.", "Plur": "мн.", "Dual": "дв."},
    "en": {"Sing": "sg.", "Plur": "pl.", "Dual": "du."},
    "el": {"Sing": "εν.", "Plur": "πλ.", "Dual": "δυ."},
}
_FMT_TENSE = {
    "ru": {"Pres": "наст.", "Past": "прош.", "Fut": "буд.", "Pqp": "плюскв."},
    "en": {"Pres": "pres.", "Past": "past", "Fut": "fut.", "Pqp": "plupf."},
    "el": {"Pres": "ενεστ.", "Past": "παρελθ.", "Fut": "μελ.", "Pqp": "υπερσ."},
}
_FMT_VOICE = {
    "ru": {"Act": "акт.", "Mid": "мед.", "Pass": "пасс."},
    "en": {"Act": "act.", "Mid": "mid.", "Pass": "pass."},
    "el": {"Act": "ενεργ.", "Mid": "μέσ.", "Pass": "παθ."},
}
_FMT_MOOD = {
    "ru": {"Ind": "изъяв.", "Sub": "сосл.", "Opt": "опт.", "Imp": "пов."},
    "en": {"Ind": "ind.", "Sub": "subj.", "Opt": "opt.", "Imp": "imp."},
    "el": {"Ind": "οριστ.", "Sub": "υποτ.", "Opt": "ευκτ.", "Imp": "προστ."},
}
_FMT_VFORM = {
    "ru": {"Fin": "личн.", "Inf": "инф.", "Part": "прич."},
    "en": {"Fin": "fin.", "Inf": "inf.", "Part": "part."},
    "el": {"Fin": "ρηματ.", "Inf": "απρφ.", "Part": "μτχ."},
}
_FMT_GENDER = {
    "ru": {"Masc": "м.", "Fem": "ж.", "Neut": "ср."},
    "en": {"Masc": "m.", "Fem": "f.", "Neut": "n."},
    "el": {"Masc": "αρσ.", "Fem": "θηλ.", "Neut": "ουδ."},
}
_FMT_PRONTYPE = {
    # "Prs": "личн.мест." (not the shorter "личн.") -- avoids colliding
    # with _FMT_VFORM's "Fin": "личн." (VerbForm and PronType never
    # co-occur in one feats dict today since verbs and pronouns are
    # disjoint pos values, but a reader comparing labels across
    # different tables shouldn't see the same abbreviation mean two
    # unrelated things). Caught in code review.
    "ru": {"Prs": "личн.мест.", "Dem": "указ.", "Rel": "относ.", "Int": "вопр.", "Ind": "неопр.", "Rcp": "взаимн."},
    "en": {"Prs": "pers.", "Dem": "dem.", "Rel": "rel.", "Int": "int.", "Ind": "indef.", "Rcp": "recip."},
    "el": {"Prs": "προσ.", "Dem": "δεικτ.", "Rel": "αναφ.", "Int": "ερωτ.", "Ind": "αόρ.", "Rcp": "αλληλ."},
}


def fmt_ud_feats(grammar_str: str, lang: str) -> str:
    """Format a UD FEATS string as a human-readable grammatical label.

    Args:
        grammar_str: UD FEATS string, e.g. ``"Tense=Pres|Mood=Ind|Person=1|Number=Sing"``.
        lang:        Target language for labels: ``"ru"``, ``"en"``, or ``"el"``.

    Returns a compact label such as ``"наст. 1 ед."`` (ru) or ``"pres. 1 sg."`` (en).
    Falls back to the original string on parse errors or unknown values.
    """
    if not grammar_str:
        return grammar_str
    try:
        feats = dict(kv.split("=") for kv in grammar_str.split("|") if "=" in kv)
    except Exception:
        return grammar_str

    c   = _FMT_CASE.get(lang,   _FMT_CASE["en"])
    n   = _FMT_NUM.get(lang,    _FMT_NUM["en"])
    t   = _FMT_TENSE.get(lang,  _FMT_TENSE["en"])
    v   = _FMT_VOICE.get(lang,  _FMT_VOICE["en"])
    m   = _FMT_MOOD.get(lang,   _FMT_MOOD["en"])
    vf  = _FMT_VFORM.get(lang,  _FMT_VFORM["en"])
    g   = _FMT_GENDER.get(lang, _FMT_GENDER["en"])
    pt  = _FMT_PRONTYPE.get(lang, _FMT_PRONTYPE["en"])

    parts = []
    if "PronType" in feats:
        parts.append(pt.get(feats["PronType"], feats["PronType"]))
    if "VerbForm" in feats:
        parts.append(vf.get(feats["VerbForm"], feats["VerbForm"]))
    if "Tense" in feats:
        parts.append(t.get(feats["Tense"], feats["Tense"]))
    if "Voice" in feats:
        parts.append(v.get(feats["Voice"], feats["Voice"]))
    if "Mood" in feats and feats.get("Mood") != "Ind":
        parts.append(m.get(feats["Mood"], feats["Mood"]))
    if "Person" in feats:
        num_lbl = n.get(feats.get("Number", ""), "")
        parts.append(f"{feats['Person']} {num_lbl}".strip())
    elif "Number" in feats:
        parts.append(n.get(feats["Number"], feats["Number"]))
    if "Case" in feats:
        parts.append(c.get(feats["Case"], feats["Case"]))
    if "Gender" in feats:
        parts.append(g.get(feats["Gender"], feats["Gender"]))

    return " ".join(parts) if parts else grammar_str
