"""Compare all backend selectors for Modern Greek and Ancient Greek.

Named backends and their defaults:
  language="el"                          → ModernGreekBackend  (default)
  language="el",  backend="modern-greek" → ModernGreekBackend  (must equal default)
  backend="modern-greek"                 → ModernGreekBackend  (language inferred)
  language="el",  backend="unimorph"     → UniMorphBackend

  language="grc"                           → AncientGreekBackend (default)
  language="grc", backend="ancient-greek"  → AncientGreekBackend (must equal default)
  backend="ancient-greek"                  → AncientGreekBackend (language inferred)
  language="grc", backend="unimorph"       → UniMorphBackend (nouns/adj only)

Run:
    uv run examples/backend_selection.py
"""

import eee


def _safe_inflect(lemma, features, pos, **kw):
    try:
        return eee.inflect(lemma, features, pos, **kw)
    except Exception as exc:
        return type(exc).__name__


def _fmt(result) -> str:
    if isinstance(result, set):
        return ", ".join(sorted(result)) if result else "(not in corpus)"
    return str(result)


def compare_all(lemma, features, pos, lang, named_backend):
    """Print default vs named-backend vs unimorph for one (lemma, features, pos)."""
    r_default  = _safe_inflect(lemma, features, pos, language=lang)
    r_named    = _safe_inflect(lemma, features, pos, language=lang, backend=named_backend)
    r_inferred = _safe_inflect(lemma, features, pos, backend=named_backend)
    r_unimorph = _safe_inflect(lemma, features, pos, language=lang, backend="unimorph")

    eq_named    = "==" if r_default == r_named    else "!="
    eq_inferred = "==" if r_default == r_inferred else "!="

    print(f"  language={lang!r:<6}                      {_fmt(r_default)}")
    print(f"  language={lang!r:<6} backend={named_backend!r:<15} {_fmt(r_named)}  {eq_named} default")
    print(f"           {'':6} backend={named_backend!r:<15} {_fmt(r_inferred)}  {eq_inferred} default  (language inferred)")
    print(f"  language={lang!r:<6} backend='unimorph'       {_fmt(r_unimorph)}")


def compare_default_vs_inferred(lemma, features, pos, lang, named_backend):
    """Print language=lang-only vs backend=name-only (language inferred)."""
    r_lang     = _safe_inflect(lemma, features, pos, language=lang)
    r_inferred = _safe_inflect(lemma, features, pos, backend=named_backend)

    eq = "==" if r_lang == r_inferred else "!="
    print(f"  language={lang!r:<6}                      → {_fmt(r_lang)}")
    print(f"           {'':6} backend={named_backend!r:<15} → {_fmt(r_inferred)}  {eq} language={lang!r}")


print("══ el: Modern Greek ══════════════════════════════════════════════════════")

print("\nακούω verb pres 1sg")
compare_all("ακούω",
    {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
    "verb", "el", "modern-greek")

print("\nακούω verb aorist 1sg")
compare_all("ακούω",
    {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
    "verb", "el", "modern-greek")

print("\nμαγκιά noun gen sg")
compare_all("μαγκιά", {"Case": "Gen", "Number": "Sing"}, "noun", "el", "modern-greek")

print("\n══ grc: Ancient Greek ════════════════════════════════════════════════════")

print("\nλύω verb aorist 1sg")
compare_all("λύω",
    {"VerbForm": "Fin", "Tense": "Aor", "Mood": "Ind", "Voice": "Act", "Person": "1", "Number": "Sing"},
    "verb", "grc", "ancient-greek")

print("\nθεός noun gen sg")
compare_all("θεός", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun", "grc", "ancient-greek")

print("\n══ default == inferred named backend ════════════════════════════════════")
print("  language=lang only  vs  backend=name only (language inferred from name)")

print("\nακούω verb pres 1sg")
compare_default_vs_inferred("ακούω",
    {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
    "verb", "el", "modern-greek")

print("\nθεός noun gen sg")
compare_default_vs_inferred("θεός",
    {"Case": "Gen", "Number": "Sing", "Gender": "Masc"},
    "noun", "grc", "ancient-greek")

print("\n══ unimorph requires language= ══════════════════════════════════════════")
try:
    eee.inflect("ακούω", {}, "verb", backend="unimorph")
except ValueError as e:
    print(f"  {e}")
