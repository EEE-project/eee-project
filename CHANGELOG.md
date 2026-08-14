# Changelog

## 1.7.0 - 2026-08-14
- `PosNotSupportedError` (previously raised only from the internal UniMorph
  tag-translation layer) is now raised by the top-level `inflect_slot()`
  whenever the resolved backend has no data at all for `pos`, checked via
  `get_slot_templates(...) is None` — the same signal every bundled
  backend already used internally, now surfaced consistently instead of
  falling through to a backend-specific `ValueError` or an ambiguous empty
  result. Distinct from a supported `pos` with no forms for one particular
  lemma/slot, which still returns an empty set as before. Message
  generalized (was hardcoded to "...not supported by the UniMorph
  translator"); constructor now accepts an optional `language` for context.
- New pronoun paradigm test/drill (`GreekUtils.check_pronoun_test`/
  `check_pronoun_slot`/`pronoun_slot_labels`/`create_pronoun_test_ui`/
  `pronoun_paradigm_drill_form`/`pronoun_drill_meta`), gendered pronouns
  only (κανένας, ίδιος, αυτός, ...; see `PRONOUN_LEMMAS_GENDERED` in
  modern-greek-inflexion-eee) — mirrors the adjective test's shape (same
  Case x Number x Gender paradigm), except `mode="full"` tests
  `nom`/`gen`/`acc` only (no pronoun has a vocative form).
- Both the adjective and pronoun tests now filter their fields to only the
  slots the backend actually has data for (`adjective_drill_meta`, a new
  sibling of the existing `noun_drill_meta`/`verb_drill_meta`) — previously
  a defective word (e.g. κανένας, which has no plural at all) showed every
  static field regardless, revealing an uninformative "must be ?" only
  after the student filled it in and checked. `adjective_paradigm_drill_form`/
  `pronoun_paradigm_drill_form` now take a required `adj_meta`/`pron_meta`
  keyword (from the matching `*_drill_meta` call), matching
  `verb_paradigm_drill_form`'s existing `verb_meta` shape.
- `examples/modern_greek_drill_notebook.py` gains "Pronouns" as a 4th
  switchable option alongside Verb/Noun/Adjective.
- Internal: the adjective and pronoun test clusters (previously ~150 lines
  of copy-pasted logic between the two) now share one Case x Number x
  Gender implementation (`_gendered_slot_list`/`_gendered_slot_names`/
  `_gendered_slot_ok`/`_gendered_drill_meta`/`_check_gendered_test`/
  `_check_gendered_slot`/`_create_gendered_test_ui`), parametrized by pos
  name, forms-lookup function, and full-mode case list. No change to any
  public method's signature or behavior.

## 1.6.0 - 2026-08-12
- `eee_footer()` takes optional `prev_url`/`next_url` and renders ◀/▶ links
  to the neighboring lesson, each omitted when there's no neighbor (start/end
  of a course). New `same_window` param (default `False`) controls prev/next
  link target, matching `eee_topbar`'s existing molab-safe convention; the
  "Source" link is unaffected.
- Add `ConfigStore.adjacent_urls(own_url)` to compute them from the same
  `index.tsv` the topbar already reads — finds the row matching `own_url`
  and returns the previous/next row's URL, so a course that skips a number
  (no chapter 5, say) skips it in navigation too, for free.

## 1.5.3 - 2026-08-12
- Fix `_source_host_base()` (1.5.2's host-aware `eee_footer()` link): used
  `js.window.location.hostname`, but marimo's Pyodide kernel runs in a Web
  Worker, where `window` doesn't exist (`from js import window` raises
  `ImportError` there) — confirmed directly against a real exported
  notebook in a browser, not just unit tests. 1.5.2's link silently fell
  back to Codeberg on every host, including GitHub/GitLab, exactly the bug
  it was meant to fix. Now uses `js.self.location.hostname` (`self` is the
  Worker's own global scope) — verified against a real WASM export before
  shipping this time.

## 1.5.2 - 2026-08-12
- `eee_footer()`'s "Source" link now points at whichever host is actually
  serving the page (Codeberg, GitHub, or GitLab), detected via Pyodide's
  `js` bridge — it previously always linked to Codeberg regardless of
  host, including on GitHub/GitLab-hosted deployments. Falls back to
  Codeberg for local `marimo edit`/`marimo run`, where no browser is
  available to detect from.
- `docs/examples.md` live-demo links now cover all 3 hosts (GitHub, GitLab,
  Codeberg) per notebook, not just Codeberg — the notebooks were already
  mirrored on all 3, the docs just hadn't caught up.

## 1.5.1 - 2026-08-09
- Fix noun/verb/adjective drills testing cells with no backend form: a
  backend can return `{''}` for a blank cell, which is truthy under
  `bool()` — switched to `any(...)` throughout.
- Add `verb_drill_meta` (verb sibling of `noun_drill_meta`); wire it into
  `create_verb_test_ui` and `verb_paradigm_drill_form`.

## 1.5.0 - 2026-08-09
- Add UI language persistence, verb-prefix/drill-focus fixes, and WASM
  export Makefile targets.

## 1.4.0 - 2026-08-04
- Add `same_window` param to `eee_topbar`/`eee_card_list` for non-molab
  hosting.

## 1.3.0 - 2026-08-04
- Fix `UnicodeEncodeError` on non-ASCII remote fetches, add concurrent
  `ensure_files()`.

## 1.2.1 - 2026-08-04
- Fix `ensure_file()` `UnicodeEncodeError` on non-ASCII filenames under
  Pyodide.

## 1.2.0 - 2026-08-04
- Fix CORS-blind remote fetch (Codeberg+GitLab): `ensure_file()`/
  `ConfigStore.from_url()` now rewrite Codeberg and GitLab git-web raw
  URLs to their CORS-safe API form at fetch time.
- Fix 3 `word_quiz`/`word_drill` call sites passing an invalid `done=`
  kwarg, and a stale example path missing the `ancient_greek/` prefix.
- `docs/examples.md` links all 6 WASM demos, not just drill.

## 1.1.0 - 2026-08-02
- Add `modern_greek_drill_notebook.py` example: verb/noun/adjective
  paradigm drills behind a part-of-speech selector, with a live
  word/translation table that shrinks as words are completed.
- Add a 10th TSV-backed UI label (`word_label`) alongside the 9 added
  for the drill's own strings, translated in en/ru/el.

## 1.0.1 - 2026-08-01
- Default the era-tab CSS switcher to the first tab instead of hiding it
  until checked, so losing `:checked` state on a re-render self-heals.
- Add a `translation_presence_not_found` UI label key for when
  `translation_presence.tsv` is missing and can't be fetched.

## 1.0.0 - 2026-07-29
- README rework, PyPI packaging (dependency constraints, install
  instructions, metadata).

## 0.10.0 - 2026-07-28
- Rename `lessons.tsv` to `index.tsv`, restore missing Modern Greek
  tenses.

## 0.9.0 - 2026-07-28
- Add `analyze()` reverse-lookup dispatch, pluperfect paradigm support,
  drill/JS cleanup.

## 0.8.0 - 2026-07-28
- Add multi-language tense/slot/widget labels, poem-lesson UI,
  `magnify_image(prefer_local=)`, shared stanza-markdown handling.

## 0.7.0 - 2026-07-21
- Add polytonic diacritics, indefinite articles, paradigm-drill
  focus-lock rewrite, Modern Greek example exercise.

## 0.6.0 - 2026-07-16
- Add paradigm-drill exercises, diachronic paradigm tables through
  Modern Greek, clickable interactive text, stanza support.

## 0.5.0 - 2026-06-21
- Add multi-language backends, `notebook_utils` UI helpers with
  diacritics widget.

## 0.4.0 - 2026-05-26
- Add unimorph backend, docs restructure, remove `analyze()`.

## 0.3.0 - 2026-05-21
- Add `examples/greek_notebook.py`: combined el/grc notebook with full
  verb/noun/adjective paradigms, particles, pronouns, and article
  columns; grc adds indicative/imperative/infinitive/participle/
  pluperfect.

## 0.2.0 - 2026-05-20
- Language-agnostic morphology API with Modern Greek (el) and Ancient
  Greek (grc) backends.

## 0.1.0 - 2026-05-20
- Initial release: language-agnostic morphology API with a Modern Greek
  (el) backend.
