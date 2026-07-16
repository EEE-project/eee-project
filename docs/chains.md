# Backend Chains

eee supports **backend chains** — an ordered list of backends tried in sequence
for a given language. Chains have no defaults and must be registered explicitly
at application startup:

```python
import eee
from ancient_greek_backend_eee import AncientGreekBackend
from unimorph_backend_eee import UniMorphBackend

eee.register_backend("grc", AncientGreekBackend(), backend="ancient-greek")
# or select a corpus lexicon:
# AncientGreekBackend(lexicons=["homer"])                     # Homeric (~2335 verbs)
# AncientGreekBackend(lexicons=["pratt", "ltrg", "lsj"])      # Classical Attic (verbs + nouns)
# AncientGreekBackend(lexicons=["homer", "lxx", "morphgnt"])  # all corpora (~5055 verbs)
eee.register_backend("grc", UniMorphBackend(), backend="unimorph")
eee.set_chain("grc", ["ancient-greek", "unimorph"])
```

When `inflect(lemma, features, pos, language="grc")` is called with `backend=None`
and a chain is registered, the chain runs with `stop="first"`: backends are tried in
order and the first non-empty result is returned. Callers that pass an explicit
`backend=` bypass the chain entirely.

## Chain API

```python
from eee import set_chain, get_chain, inflect_traced

# Override the default chain for grc
set_chain("grc", ["ancient-greek", "unimorph"])

# Per-call chain override (does not modify the registry)
result = inflect_traced("θεός", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun",
                        language="grc", chain=["unimorph", "ancient-greek"])

# Union mode — aggregate results from all backends
result = inflect_traced("θεός", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun",
                        language="grc", stop="all")
```

`inflect_traced()` returns an `InflectResult` with:
- `forms` — the inflected forms
- `source` — backend key that produced the result (e.g. `"grc:unimorph"`), or `None` for `stop="all"`
- `tried` — backend keys attempted in order
- `by_backend` — maps each backend key that ran to the forms it returned; useful for attribution with `stop="all"`

## Hook extension points

Hooks are optional callables that wrap the chain for preprocessing or
post-processing:

```python
from eee import HookContext

def normalize(lemma, features, pos, ctx: HookContext):
    """Pre-hook: rewrite inputs before any backend sees them."""
    return lemma.strip(), features, pos

def gap_fill(forms: set[str], ctx: HookContext) -> set[str]:
    """Post-hook: extend or filter results after the chain completes."""
    if not forms:
        # e.g., call an LLM backend here
        pass
    return forms

set_chain("grc", ["ancient-greek", "unimorph"],
          pre_hook=normalize, post_hook=gap_fill)
```

Pre-hooks run once before the chain starts; post-hooks run once after all
backends have been tried and the stop condition applied.

Per-call hooks override the chain's registered hooks for that call only:

```python
inflect_traced("θεός", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun",
               language="grc", post_hook=gap_fill)
```

Hook exceptions propagate to the caller (unlike backend exceptions, which are
swallowed and logged at DEBUG level).

See `examples/backend_chain.py` and `examples/chain_hooks.py` for complete
worked examples.
