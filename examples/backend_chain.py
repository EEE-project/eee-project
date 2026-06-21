# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "eee @ git+https://codeberg.org/EEE-project/eee.git",
#     "unimorph-backend-eee @ git+https://codeberg.org/EEE-project/unimorph-backend-eee.git",
#     "ancient-greek-backend-eee @ git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee = { git = "https://codeberg.org/EEE-project/eee.git" }
# unimorph-backend-eee = { git = "https://codeberg.org/EEE-project/unimorph-backend-eee.git" }
# ancient-greek-backend-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-backend-eee.git" }
# ///
"""Backend chain example.

Shows:
  - Default chain coverage for grc (θεός and βοηθός both return results)
  - inflect_traced() InflectResult — forms, source, tried, by_backend
  - stop="all" to union results from all backends

Run standalone:
    uv run examples/backend_chain.py
"""
from __future__ import annotations

import eee_project as eee
from eee_project import inflect_traced
from ancient_greek_backend_eee import AncientGreekBackend
from unimorph_backend_eee import UniMorphBackend

eee.register_backend("grc", AncientGreekBackend(), backend="ancient-greek")
eee.register_backend("grc", UniMorphBackend(), backend="unimorph")
eee.set_chain("grc", ["ancient-greek", "unimorph"])

SLOTS = [
    ("Nom Sg", {"Case": "Nom", "Number": "Sing"}),
    ("Gen Sg", {"Case": "Gen", "Number": "Sing"}),
    ("Acc Sg", {"Case": "Acc", "Number": "Sing"}),
]


def show(lemma: str, stop: str = "first") -> None:
    print(f"\n{lemma!r}  stop={stop!r}")
    last_r = None
    for label, features in SLOTS:
        last_r = inflect_traced(lemma, features | {"Gender": "Masc"}, "noun",
                                language="grc", stop=stop)
        src = last_r.source or "(union)"
        print(f"  {label}: {sorted(last_r.forms)}  source={src}")
    if stop == "all" and last_r is not None:
        print(f"  by_backend: { {k: sorted(v) for k, v in last_r.by_backend.items()} }")


# θεός — in ancient-greek backend (source should be grc:ancient-greek)
show("θεός")

# βοηθός — in unimorph grc corpus (source should be grc:unimorph)
show("βοηθός")

# stop="all" — union of both backends, with per-backend attribution
show("θεός", stop="all")
