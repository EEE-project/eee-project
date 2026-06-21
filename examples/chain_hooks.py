# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "eee-project @ git+https://codeberg.org/EEE-project/eee.git",
#     "unimorph-backend-eee @ git+https://codeberg.org/EEE-project/unimorph-backend-eee.git",
#     "ancient-greek-backend-eee @ git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee.git" }
# unimorph-backend-eee = { git = "https://codeberg.org/EEE-project/unimorph-backend-eee.git" }
# ancient-greek-backend-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-backend-eee.git" }
# ///
"""Chain hook examples.

Shows:
  - pre_hook: normalize a lemma before it reaches any backend
  - post_hook: gap-fill logging pattern
  - Per-call hook override vs registered hook

Run standalone:
    uv run examples/chain_hooks.py
"""
from __future__ import annotations

import eee_project as eee
from eee_project import inflect_traced, set_chain, HookContext
from ancient_greek_backend_eee import AncientGreekBackend
from unimorph_backend_eee import UniMorphBackend

eee.register_backend("grc", AncientGreekBackend(), backend="ancient-greek")
eee.register_backend("grc", UniMorphBackend(), backend="unimorph")


# ── pre_hook: strip whitespace ────────────────────────────────────────────────

def normalize_lemma(
    lemma: str,
    features: dict[str, str],
    pos: str,
    ctx: HookContext,
) -> tuple[str, dict[str, str], str]:
    return lemma.strip(), features, pos


# ── post_hook: log gaps where all backends miss ───────────────────────────────

def log_gaps(forms: set[str], ctx: HookContext) -> set[str]:
    if not forms:
        print(f"  [gap] {ctx.lemma!r} ({ctx.pos}) not found in: {ctx.tried}")
    return forms


# Register hooks permanently for grc
set_chain("grc", ["ancient-greek", "unimorph"], pre_hook=normalize_lemma, post_hook=log_gaps)

FEATURES = {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}

# θεός — found; log_gaps does not fire
result = inflect_traced("θεός", FEATURES, "noun", language="grc")
print(f"θεός Nom Sg → {sorted(result.forms)}  (source: {result.source})")

# Demonstrate per-call hook override (registered post_hook is replaced for this call)
result2 = inflect_traced("θεός", FEATURES, "noun", language="grc",
                          post_hook=lambda forms, ctx: forms | {"__custom__"})
print(f"θεός with per-call hook → {sorted(result2.forms)}")
