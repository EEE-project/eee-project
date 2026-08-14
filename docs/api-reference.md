# API Reference

Full function-by-function reference for the `eee` package. For notebook-authoring
patterns (`GreekUtils`, slot templates in practice, drill widgets), see
[api-patterns.md](api-patterns.md). For backend chains and hooks in depth, see
[chains.md](chains.md).

### `eee.inflect(lemma, features, pos, *, language, backend=None) → set[str]`

Returns inflected forms matching the UD feature bundle. Returns an empty set if the form doesn't exist in the paradigm.

- `pos`: `"verb"`, `"noun"`, `"adjective"`, `"adverb"`
- `language`: IETF tag — `"el"`, `"grc"`, etc. Required unless `backend` names a single-language backend (e.g. `backend="modern-greek"` infers `language="el"`).
- `backend`: named variant — `"unimorph"`, `"modern-greek"`, `"ancient-greek"`. `None` selects the default or runs the registered chain.

### `eee.inflect_traced(lemma, features, pos, *, language, backend=None, chain=None, stop="first") → InflectResult`

Like `inflect()` but returns an `InflectResult` with `.forms`, `.source`, `.tried`, and `.by_backend`.

### `eee.list_lemmas(pos, language=None, backend=None) → list[str]`

Returns lemmas available in the backend's corpus for `pos`. With `backend=None` and a chain registered, queries every chain backend and returns a deduplicated union. Returns `[]` for algorithm-based backends with no finite vocabulary, or backends without `list_lemmas()`.

### `eee.list_lemmas_traced(pos, language, backend=None) → list[LemmaEntry]`

Like `list_lemmas()` but returns one `LemmaEntry(lemma, source)` per `(lemma, backend)` pair — duplicates across chain backends are **not** collapsed, so a lemma present in two backends appears twice with different `.source` values.

### `eee.analyze(form, language=None, backend=None) → list[dict]`

Reverse lookup: candidate morphological analyses for a surface form, each a `{"lemma", "pos", "tag", "features"}` dict (`features` is a UD FEATS dict). With `backend=None` and a chain registered, queries every chain backend and returns a deduplicated union (by lemma+pos+tag). Returns `[]` for a form matching nothing, or for backends without `analyze()`. Ambiguous by design — a syncretic surface form commonly yields multiple candidates; disambiguation is left to the caller.

### `eee.analyze_traced(form, language, backend=None) → list[AnalysisEntry]`

Like `analyze()` but returns one `AnalysisEntry(lemma, pos, tag, features, source)` per `(candidate, backend)` pair — duplicates across chain backends are **not** collapsed.

### `eee.supported_languages() → dict[str, list[str]]`

Returns `{language_code: [entry_point_value, ...]}` for entry-point-discovered backends. Multiple backends may register for the same language code; all are listed. Does not include explicitly registered backends or the fallback.

### `eee.register_backend(code, instance, backend=None) → None`

Register a backend instance. Pass `backend='name'` to register a named variant alongside the default.

### `eee.set_fallback_backend(instance) → None`

Catch-all for all unregistered language codes.

### `eee.set_chain(language, backends, *, pre_hook=None, post_hook=None) → None`

Register an ordered list of backend names for a language. Backends are tried in order; the first non-empty result is returned (`stop="first"`). See [chains.md](chains.md) for the full chain API, union mode, and hooks.

- `pre_hook`: `callable(lemma, features, pos, ctx) → (lemma, features, pos)` — transform inputs before the chain runs.
- `post_hook`: `callable(forms, ctx) → set[str]` — transform or supplement results after the chain runs. Used as an LLM gap-filler when `not forms`.

### `eee.language_info(code) → dict | None`

Return the manifest entry for a language code (name, tier, pos list), or `None` if unknown.

## Slot templates

Slot templates map human-readable labels to backend-native tags, enabling structured inflection tables for any language.

```python
from eee_project import SlotTemplate, inflect_slot, get_slot_templates, register_tag_type

# Inflect a single slot
slot = SlotTemplate(label="Present 3sg", tag_type="unimorph", tag="V;PRS;3;SG")
forms = eee.inflect_slot("λύω", slot, "verb", language="el")  # → {"λύει"}

# Pass an explicit backend instance (required for non-registered languages)
from unimorph_backend_eee import UniMorphBackend
backend = UniMorphBackend("jpn")
forms = eee.inflect_slot("歌う", slot, "verb", language="jpn", backend=backend)

# Load a saved TOML template via the active backend
slots = eee.get_slot_templates("ail", "verb", terms_lang="en")
# → list[SlotTemplate] or None

# Register a custom tag type
eee.register_tag_type("mytags", lambda backend, lemma, slot, pos, lang: {slot.tag})
```

`SlotTemplate` fields: `label` (str), `tag_type` (str), `tag` (str), `features` (Mapping[str, str] | None).
Built-in tag types: `"unimorph"` (direct tag lookup), `"ud"` (UD features dict via `slot.features`).

For `tag_type="ud"`, `tag` is auto-derived as feature values joined in sorted-key order (e.g. `{"Case": "Nom", "Number": "Sing"}` → `"Nom;Sing"`).

`inflect_slot` accepts an optional `backend=` keyword: a named variant string (e.g. `"unimorph"`), an explicit backend instance, or `None` to use the default registered backend. Pass an instance for languages not registered with eee (e.g. non-bundled UniMorph languages).

## Adding a Language

Implement two methods and register:

```python
class MyBackend:
    language = "xx"
    def inflect(self, lemma, features, pos, language=None, **kw): ...

eee.register_backend("xx", MyBackend())
# Named variant:
eee.register_backend("xx", MyBackend(), backend="my-backend")
```

Or ship as a package with an entry point (auto-discovered on install):

```toml
[project.entry-points."eee_project.backends.v1"]
xx = "my_xx_eee.backend:MyBackend"

# Optional: register a friendly name so callers can use backend="my-backend"
[project.entry-points."eee_project.named_backends.v1"]
my-backend = "my_xx_eee.backend:MyBackend"
```

## Exceptions

| Exception | Raised when |
|-----------|-------------|
| `eee.UnsupportedLanguageError` | No backend registered for `language` / `backend` combination |
| `eee.BackendLoadError` | Backend found but failed to load |
| `eee.PosNotSupportedError` | The resolved backend has no data at all for `pos` (checked via `get_slot_templates(...) is None`) — raised by `inflect_slot()`. Distinct from a supported `pos` that simply has no forms for one particular lemma/slot, which still returns an empty set. |

**Chain vs. single backend — different failure handling, on purpose.** With
`chain=[...]` (or a registered chain), a backend that fails to load or raises
during `inflect()` is logged and skipped — the chain tries the next backend.
With an explicit `backend=` or the resolved default backend (no chain
registered), the same failure *raises* `UnsupportedLanguageError` /
`BackendLoadError` instead — there's no fallback to skip to, so silently
returning an empty result would hide a real configuration error. See
`test_named_backend_does_not_fall_through_to_fallback` /
`test_backend_exception_is_skipped` for both behaviors under test.
