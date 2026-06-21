"""Compare backend selectors for Modern Greek and Ancient Greek.

Named backends:
  language="el"                           → ModernGreekBackend (default)
  language="el",  backend="modern-greek"  → ModernGreekBackend
  language="el",  backend="unimorph"      → UniMorphBackend

  language="grc"                          → chain: ancient-greek → unimorph
  language="grc", backend="ancient-greek" → AncientGreekBackend only
  language="grc", backend="unimorph"      → UniMorphBackend only (nouns/adj)

  language= is always required.

Run:
    uv run examples/backend_selection.py
"""

import eee_project as eee
from eee_project import inflect_traced
from ancient_greek_backend_eee import AncientGreekBackend
from modern_greek_backend_eee import ModernGreekBackend
from unimorph_backend_eee import UniMorphBackend

eee.register_backend("el", ModernGreekBackend())
eee.register_backend("el", ModernGreekBackend(), backend="modern-greek")
eee.register_backend("el", UniMorphBackend(), backend="unimorph")
eee.register_backend("grc", AncientGreekBackend())
eee.register_backend("grc", AncientGreekBackend(), backend="ancient-greek")
eee.register_backend("grc", UniMorphBackend(), backend="unimorph")
eee.set_chain("grc", ["ancient-greek", "unimorph"])


def _safe_inflect(lemma, features, pos, **kw):
    try:
        return eee.inflect(lemma, features, pos, **kw)
    except Exception as exc:
        return type(exc).__name__


def _safe_inflect_traced(lemma, features, pos, **kw):
    try:
        return inflect_traced(lemma, features, pos, **kw)
    except Exception as exc:
        return type(exc).__name__


def _fmt(result) -> str:
    if isinstance(result, set):
        return ", ".join(sorted(result)) if result else "(not in corpus)"
    return str(result)


def compare(lemma, features, pos, lang, named_backend):
    """Print default vs named backend vs unimorph."""
    r_traced   = _safe_inflect_traced(lemma, features, pos, language=lang)
    r_named    = _safe_inflect(lemma, features, pos, language=lang, backend=named_backend)
    r_unimorph = _safe_inflect(lemma, features, pos, language=lang, backend="unimorph")

    if hasattr(r_traced, "forms"):
        r_default = r_traced.forms
        src = f"  [{r_traced.source}]" if r_traced.source else ""
    else:
        r_default = r_traced
        src = ""

    if isinstance(r_default, str) or isinstance(r_named, str):
        eq = "(err)"
    else:
        eq = "==" if r_default == r_named else "!="
    w = 20
    print(f"  language={lang!r:<6}                        {_fmt(r_default)}{src}")
    print(f"  language={lang!r:<6} backend={named_backend!r:<{w}} {_fmt(r_named)}  {eq} default")
    print(f"  language={lang!r:<6} backend='unimorph'       {_fmt(r_unimorph)}")


print("══ el: Modern Greek ══════════════════════════════════════════════════════")

print("\nακούω verb pres 1sg")
compare("ακούω",
    {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
    "verb", "el", "modern-greek")

print("\nακούω verb aorist 1sg")
compare("ακούω",
    {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
    "verb", "el", "modern-greek")

print("\nμαγκιά noun gen sg")
compare("μαγκιά", {"Case": "Gen", "Number": "Sing"}, "noun", "el", "modern-greek")

print("\n══ grc: Ancient Greek ════════════════════════════════════════════════════")

print("\nλύω verb aorist 1sg  (unimorph has no grc verbs)")
compare("λύω",
    {"VerbForm": "Fin", "Tense": "Aor", "Mood": "Ind", "Voice": "Act", "Person": "1", "Number": "Sing"},
    "verb", "grc", "ancient-greek")

print("\nθεός noun gen sg  (in ancient-greek, absent from unimorph)")
compare("θεός", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun", "grc", "ancient-greek")

print("\nβοηθός noun gen sg  (absent from ancient-greek, in unimorph)")
compare("βοηθός", {"Case": "Gen", "Number": "Sing"}, "noun", "grc", "ancient-greek")

print("\n══ inflect_traced(): attribution ════════════════════════════════════════")

eee.set_chain("grc", ["ancient-greek", "unimorph"])

for lemma in ("θεός", "βοηθός"):
    result = inflect_traced(lemma, {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun",
                            language="grc")
    print(f"  {lemma} Gen Sg → {sorted(result.forms)}  source={result.source}  tried={result.tried}")

print("\n══ language= is always required ══════════════════════════════════════════")
try:
    eee.inflect("ακούω", {}, "verb")
except ValueError as e:
    print(f"  {e}")
