# Changelog

## 1.9.0 - 2026-08-20
- Consolidated `_QUIZ_CASE_LABEL`/`_QUIZ_NUM_LABEL`/`_QUIZ_ADJ_GENDER`/
  `_QUIZ_ADJ_NUM` (noun/adjective quiz-label fallbacks) and `_GRC_NL`/
  `_GRC_DL`/`_GRC_PROW`/`_GRC_INF_LBL`/`_GRC_IMP_LBL` (grc paradigm-table
  labels) — 9 dicts total — to derive from `_grammar_fmt.py`'s existing
  `_FMT_CASE`/`_FMT_NUM`/`_FMT_GENDER`/`_FMT_VFORM`/`_FMT_MOOD` (re-keyed to
  match each dict's own key format) instead of separately hand-authoring
  the same case/number/gender/mood translations a third and fourth time.
  Every derivation was verified byte-identical to the values it replaced
  before being applied — the one exception, `_QUIZ_ADJ_GENDER`, *did*
  change: its fallback text is now the terser "m."/"ж."/"θηλ." (matching
  `_FMT_GENDER`'s own register) instead of the fuller "Masc"/"Муж"/"Θηλ" it
  had before — accepted deliberately, since it's a rarely-hit by_feats
  template fallback, and a second independently-maintained gender-
  translation table wasn't worth keeping just to preserve that. `_GRC_TCOL`
  and `_EL_VERB_COL_LBL` (Tense+Aspect+Voice/Mood compound labels — "Aor.
  Mid.", "Fut. cont.") aren't derived from `_grammar_fmt.py` — no
  `_FMT_ASPECT` dict exists, and `_FMT_TENSE` alone can't distinguish
  imperfect from aorist (both are UD `Past`) — but see below: they moved
  onto the TSV mechanism directly instead of staying hand-authored.
- Closed the gap the above left open: `_GRC_TCOL`/`_GRC_DEFAULT_CAPTION`/
  `_EL_VERB_COL_LBL`/`_EL_VOICE_CAP`/`_EL_DEFAULT_CAPTION` were still
  Python-literal `{lang: ...}` dicts with a fixed `ru`/`en`/`el` key set —
  real per-language text, just not in a TSV, so (unlike `ui_label()`)
  adding a 4th language would have meant editing this file's source rather
  than dropping in a file. Now backed by 18 new flat `ui-{lang}.tsv` keys
  (`grc_tense_pai`, `el_verb_col_pres`, `el_voice_cap_act`,
  `grc_default_caption`, `el_default_caption`, etc.): the two default-
  caption strings are plain `_ui_label(key, lang)` calls at their one use
  site each (no module dict needed — a dict + `.get(lang, d["en"])` at the
  call site would only re-implement `_ui_label()`'s own en-fallback); the
  3 genuinely compound ones (`_GRC_TCOL`, `_EL_VERB_COL_LBL`,
  `_EL_VOICE_CAP`) share one 2-line helper, `_lang_map(keys, tsv_key_fn)`,
  iterated over a new `_UI_LANGS` (every language `_load_ui_labels()`
  discovered) instead of a hardcoded tuple — so all 5 share the same
  zero-code-change extensibility as the rest of the UI-chrome layer.
  `_GRC_PROW` (person+number row labels) turned out to already have a
  byte-identical equivalent in `fmt_ud_feats()` itself — `"{person} {number}"`
  is exactly what that formatter builds — so it now calls that instead of
  re-deriving the same text from `_FMT_NUM` a second way. Verified
  byte-identical to the values each replaced before applying, plus a new
  test (`test_grc_el_compound_dicts_track_ui_langs_not_a_fixed_literal`)
  asserting each of the 3 remaining dicts' key sets equal `_UI_LANGS` by
  construction, not a literal. Full suite 1374/1374, ruff clean.
  `_EL_VOICE_CAP`'s en/el values are now identical to `_grammar_fmt.py`'s
  own `_FMT_VOICE`, but its ru text ("действ."/"страд.") was deliberately
  left as its own pre-existing wording rather than switched to
  `_FMT_VOICE`'s ru ("акт."/"пасс.") — that would be a visible rendering
  change for ru notebooks, not a pure refactor, and the two dicts having
  independent ru wording predates this release.
- Fixed the biggest gap found this release: the wrong-answer feedback text
  for all four parts of speech (`check_verb_test`/`check_noun_test`/
  `check_adjective_test`/`check_pronoun_test`, and their shared
  `_check_gendered_test` core) was hardcoded English ("entered ..., must be
  ...", "article missing", "Write with ...", "Please fill in at least one
  gender form") regardless of the notebook's language — none of these
  methods took a `lang` parameter at all. Traceable directly to a live
  report earlier in this same release's work: `❌ [εγώ:]: entered "θα
  είμαι", must be θα unknown` — "εγώ" is correctly Greek (a slot label,
  language-independent by design), but "entered"/"must be" were leaking
  through in what should have been an all-Russian message. Worse: even
  `verb_paradigm_drill_form`/`noun_paradigm_drill_form`/
  `adjective_paradigm_drill_form`/`pronoun_paradigm_drill_form` themselves —
  the most-used functions in the whole library — had no `lang` parameter to
  thread through, unlike nearly everything else in this file. Fixed at
  every layer: the 4 checkers gained `lang: str = "ru"` and route their
  messages through 7 new TSV-backed templates; `create_verb_test_ui`/
  `create_adjective_test_ui`/`_create_gendered_test_ui` (interactive-widget
  builders in the same "Pattern B" family, also live in production —
  confirmed via Kapodistrias/Zorba notebook usage, not dead code as first
  assumed) gained `lang` too; and all 4 `*_paradigm_drill_form` functions
  now accept `lang` and thread it to their internal `full_check` callback.
  `noun_slot_labels`/`_gendered_slot_names`'s own English-only fallback
  dicts (`_QUIZ_CASE_LABEL`/`_QUIZ_NUM_LABEL`/`_QUIZ_ADJ_NUM`/
  `_QUIZ_ADJ_GENDER`) are now real `{lang: ...}` dicts too — three of them
  derived directly from `_grammar_fmt.py`'s existing `_FMT_CASE`/`_FMT_NUM`
  (re-keyed, not re-authored, so they can't drift out of sync); the fourth
  genuinely differs in register (standalone slot label vs. compact inline
  abbreviation) and stays independently authored. `lang` defaults to `"ru"`
  everywhere, matching this library's own convention — omitting it now
  degrades to Russian instead of the old hardcoded English, so pass it
  explicitly (`language_selector.value`) for an EN/EL notebook session; the
  created_with_eee notebook side of actually wiring this through is a
  separate, follow-up pass. Verified with 5 new end-to-end tests confirming
  `lang` genuinely reaches the checker through each of the 4 drill-form
  functions (not just at the checker level), plus fixed 15 pre-existing
  tests across two test files that had asserted on the old hardcoded-English
  text. Full suite 1372/1372, ruff clean.
- Removed `create_pronoun_test_ui` (dead code — zero real callers anywhere
  in `created_with_eee`, only its own now-also-removed test class; the rest
  of the "Pattern B" `create_*_test_ui` family it belonged to — noun/verb/
  adjective — is genuinely still in active use by Kapodistrias/Zorba
  notebooks, confirmed above before ruling anything else out).
  `_create_gendered_test_ui` (its shared implementation with
  `create_adjective_test_ui`) stays — still has one real caller.
- Migrated `eee_card_list`'s two remaining inline `{"ru": ..., "en": ..., "el": ...}` dicts (the "coming soon" card label and the "couldn't load file" error message, the latter with an embedded `{url}`) onto the same `ui_label()`/TSV mechanism as everything else this release, preserving the function's own `lang_fallback` parameter exactly (its fallback chain is `lang` → `lang_fallback`, not the usual `ui_label()` "always fall back to en" — confirmed unchanged by 3 pre-existing tests covering exactly this fallback edge case). `eee_topbar`/`eee_hero`'s own `titles` parameters were checked too and are correctly left alone — those are caller-supplied per-course content (each notebook's own topbar-setup cell passes its own title dict in), not something this library should own.
- Fixed the same "fixed English literal regardless of lang" gap in `build_grc_paradigm_table`'s own default table caption (shown when neither `_cap` nor the word's `lexicon_tag` is given) — previously always the literal `"ancient-greek"` even for `lang="ru"`/`"el"` tables; now `_GRC_DEFAULT_CAPTION`-backed like its already-fixed Modern-Greek counterpart (`_EL_DEFAULT_CAPTION`, whose English value was also corrected from `"modern greek"` to `"modern-greek"` for consistency with the grc side's identifier-style caption text). This one is a genuine visible change to the *default* (`lang="ru"`) rendering, not just an additive language option — the old behavior was itself the bug.
- Made `build_grc_paradigm_table`/`build_modern_paradigm_table` (the Ancient-
  and Modern-Greek diachronic paradigm-table HTML renderers) genuinely
  multi-language. Both already accepted a `lang` parameter — including a
  second, per-call override on the returned closure itself — but it was
  only ever forwarded to `get_slot_templates()` (a backend call); every row/
  column label came from module-level constants with no language axis at
  all (`_GRC_NL`/`_GRC_DL`/`_GRC_TCOL`/`_GRC_PROW`/`_GRC_INF_LBL`/
  `_GRC_IMP_LBL`, `_EL_VERB_COLS`, and an inline Active/Passive caption
  tuple), so `lang="en"` silently produced identically Russian-labeled
  tables. One of these (`_GRC_CL`, the case-label lookup) was already
  reading from `_grammar_fmt.py`'s already-multilingual `_FMT_CASE` dict but
  hardcoded to `["ru"]` — now reads `_FMT_CASE.get(lang, _FMT_CASE["en"])`
  properly. The rest are now `{lang: {code: label}}` dicts with real EN/EL
  grammar-abbreviation translations authored (case/tense/mood/number/voice
  labels), matching `_grammar_fmt.py`'s existing style. Also fixed the same
  gap in the "word missing in this paradigm" note both renderers show,
  reusing the `word_missing_in_paradigm` key from earlier in this release.
  Verified against the real `ModernGreekBackend` (not a stub) for the
  Modern-Greek renderer, plus 10 new tests covering both renderers across
  en/el, confirming old vs. new label text is mutually exclusive in the
  output (not just that the new text appears). Full suite 1371/1371, ruff
  clean.
- Made `make_renew_button`/`ictus_toggle_panel`/`render_gloss_panel`
  (Odyssey's renew-sample button, ictus/Homer-lexicon toggle note, and
  word-click gloss panel) properly multi-language via `ui_label()` — they
  previously had no `lang` parameter at all and always rendered in Russian
  regardless of the notebook's own language setting. Also fixed an isolated
  case of the same gap inside `word_quiz_form` (which already takes `lang`
  everywhere else): the "missing in the paradigm of {lemma}" fallback
  message was hardcoded Russian even when called with `lang="en"`/`"el"`.
  `_load_ui_labels()` now discovers language files by name
  (`ui-*.tsv`) instead of a fixed `("en", "ru", "el")` tuple, so adding a
  new language going forward is purely a data change — drop in
  `ui-{lang}.tsv` with the same columns, no code change needed. Also
  reworded docstrings/comments that illustrated button/exercise names using
  their Russian-default rendering (`"Проверить" button`, `да/нет` radio) to
  use English prose instead, for consistency with the rest of the file's
  documentation. Verified against the real `marimo` package (not just test
  stubs) for all three languages, plus 6 new unit tests and a corrected
  regression test that had drifted to checking only about half the real
  keys (a hand-maintained key list from before this session's TSV growth —
  now iterates `_UI_LABELS` itself so it can't drift again). Full suite
  1361/1361, ruff clean.
- Migrated the last 24 hardcoded `{"ru": ..., "en": ..., "el": ...}` UI-chrome
  string dicts in `notebook_utils.py` (button labels, quiz/stanza-match/
  translation-presence widget text, the footer's "Source:" label) onto
  `data/labels/ui-{lang}.tsv` + `ui_label()` — the same mechanism already
  used for other widget chrome, now used for all of it. These dicts predated
  that mechanism (added in v0.6.0, one version before `ui_label()` existed)
  and were never migrated when it arrived. A nested dict (`_QUIZ_POS`, POS
  abbreviations) and a tuple-valued one (`_YES_NO`) don't fit `ui_label()`'s
  plain `key → string` shape, so each was flattened into several flat keys
  (`quiz_pos_noun`/`quiz_pos_verb`/`quiz_pos_adj`/`quiz_pos_adv`,
  `yes_label`/`no_label`) instead of extending the mechanism itself. Added a
  module-level `_ui_label()` twin of the `GreekUtils.ui_label()` method so
  `eee_footer` (a plain function, no `self`) can share the same lookup.
  Purely internal — no public function signature changed. Verified
  behavior-preserving: full test suite unchanged (1355 passing, including
  pre-existing exact-string assertions per language for several of these),
  plus a direct check of the two flattened lookups' fallback behavior for
  an unrecognized key (matches the original dict `.get(key, default)`
  semantics exactly) and the one format-string value's `.format()` round
  trip. Retry-mistakes button text is shortened as part of this pass, from
  "↺ Retry mistakes"/"Повторить ошибки"/"Επανάληψη λαθών" to a plain
  "Errors"/"Ошибки"/"Λάθη" — the only actual text change in this pass, the
  rest is byte-identical to before.
- Added a "retry mistakes" mode to the shared paradigm-drill engine
  (`_paradigm_drill_form`, backing `verb_paradigm_drill_form`/
  `noun_paradigm_drill_form`/`adjective_paradigm_drill_form`/
  `pronoun_paradigm_drill_form` — all four parts of speech get it for
  free). Tracks a per-word wrong-answer count for the session
  (`make_error_tracking_state`, `{word: count}`, incremented once per wrong
  attempt -- a wrong "Check" click or a wrong per-field Enter both count,
  since per-field Enter-navigation is this drill's primary interaction, not
  a secondary path to the button) and adds a `retry_mistakes_button` that
  starts a fresh round over only the words with a recorded mistake. Counts
  are scoped to "this round": the whole dict clears when a fresh round
  starts (restart or retry), but nothing clears mid-round, so a mistake
  self-corrected within the same attempt still counts. Landed in two
  passes after live testing: clearing forever (first cut) let a word fixed
  in an earlier retry round keep resurfacing in every later "retry
  mistakes" click; clearing per-word on that word's own next correct
  answer (second cut) over-corrected it, making a self-corrected mistake
  vanish before the round even ended. Clearing only at round boundaries
  satisfies both. Also added a small error-count indicator (`❌ N`) next
  to the drill's progress line and on the done screen, showing the current
  tally so it's visible, not just tracked internally. Entirely opt-in: `get_errors`/
  `set_errors`/`get_retry_cnt`/`set_retry_cnt`/`retry_btn` all default to
  `None`, and existing calls that don't pass them keep their exact previous
  behavior — verified via the existing full test suite passing unchanged,
  plus new tests, plus a live session against the real chapter_08 notebook.
  Also fixed (confirmed live): the drill's "N / total" progress line
  divided by `len(vocab)` (the *original*, full word list) even during a
  retry round over a smaller subset, e.g. showing "2 / 2" for a 1-word
  retry round instead of "1 / 1". `len(words) + len(hist)` is already this
  round's exact size regardless of which round it is -- both only ever
  move a word between each other, and both reset at every round boundary
  -- so no new state was needed, just using what was already there. Also
  reshaped the done-screen error indicator from "total mistake count /
  word count" (e.g. "4 / 2" for 4 wrong attempts across 2 words -- a
  ratio that can exceed 1 and reads as broken) to "words with a mistake /
  this round's size" (e.g. "1 / 2"), the same round-relative fix applied
  to this second, separate spot.
- Fixed verb checking (`_verb_forms`, backing `verb_drill_meta`/
  `check_verb_test`/`check_verb_slot`) rejecting correct answers for
  aspectually defective Modern Greek verbs (e.g. `είμαι` "to be", which has
  no perfective/aorist stem at all, so no distinct Simple Future/Simple
  Subjunctive/Simple Conditional exists for it). The checker looked up the
  perfective-based forms for these tenses, found nothing, showed "must be θα
  unknown", and rejected the textbook-correct answer (`θα είμαι`, built from
  the present/imperfective stem — the only future this class of verb has).
  Added `GreekConfig.defective_fallback` (`future`→`future_continuous`,
  `subjunctive_simple`→`subjunctive_continuous`, `conditional_simple`→
  `conditional_continuous` for Modern Greek; empty for Ancient Greek) so
  `_verb_forms` substitutes the continuous-tense forms whenever a tense is
  genuinely empty for a verb. This also fixes `verb_drill_meta`'s
  `active_slots`, which reads through the same function: it now shows every
  person because each one has a real (substituted) answer, not because its
  own separate "no data anywhere" fallback blindly showed every slot with
  nothing to check them against.

## 1.8.1 - 2026-08-18
- Fixed pluralia-tantum noun checking (`check_noun_test`/`check_noun_slot`/
  `noun_drill_meta`): a word stored in vocab TSVs as its own plural surface
  form (e.g. `τα σκουπίδια` — the only sensible way to write a plural-only
  noun) was being fed into the inflection backend as if that surface form
  were the nominative-singular lemma needing inflection, for its own
  `(pl, nom)` check. The backend has no way to know the input isn't a real
  lemma and can match its ending against an unrelated declension pattern —
  `σκουπίδια`'s `-ία` matched a `κυρία -> κυρίες`-style feminine paradigm,
  fabricating `σκουπίδιες` as the "correct" plural and rejecting the
  actually-correct `σκουπίδια` a student typed. Fixed by using the given
  surface form directly for a pluralia-tantum noun's own `(pl, nom)` cell
  instead of re-deriving it through the backend.
  Also restored Accusative/Genitive Plural for **neuter** pluralia-tantum
  nouns (article `τα`) instead of dropping them: Accusative is Nominative
  verbatim (Modern Greek neuter nouns always have Nom = Acc = Voc, a
  grammatical certainty, not a guess); Genitive is recovered via a
  candidate singular lemma (stripping the plural's final vowel — the
  `-ι/-ια` and `-ί/-ιά` classes both singularize this way) that's only
  trusted once it round-trips (re-inflecting it for `(pl, nom)` must
  reproduce the given surface form exactly) — confirmed safe against every
  neuter pluralia-tantum word actually in a course TSV as of this fix
  (`σκουπίδια`, `ρεβίθια`, `όσπρια`, `ζυμαρικά`, `γεμιστά`, `φασολάκια`,
  `κοινόχρηστα`, `ψώνια`, `συγχαρητήρια`, `υδραυλικά`). **Masculine/feminine**
  pluralia-tantum nouns (article `οι`) stay Nominative-Plural-only: checked
  and found genuinely ambiguous (`κανόνες` round-trips against both
  `κανόνας` and `κανόνα` but they disagree on genitive plural — `κανόνων`
  vs `κανονών` — with no way to tell which is real from round-tripping
  alone), so nothing is guessed for that case rather than risking a second
  fabricated "correct" answer.

## 1.8.0 - 2026-08-17
- Added `GreekUtils.vocab_table(df, *, select_state=None, initial_selection=None)`
  — builds a full-page (`page_size=len(df)`, no pagination) multi-select
  `mo.ui.table`, or `None` if `df` is `None`. `select_state` accepts an
  optional 0-arg getter for a persisted selection (defaulting to every row
  selected when nothing's persisted yet) and computes `len(df)` once,
  reusing it for both `page_size` and the select-all fallback, instead of a
  call site computing it twice. Extracted from `created_with_eee`, where
  `page_size=len(df)` had been hand-inserted at 191 near-identical call
  sites across every course notebook with no shared helper to call instead.
- Added `GreekUtils.load_vocab_table(filename, *, nb_dir, remote_base=None,
  file_upload=None, ru_variant=False, language=None)` — the DataFrame
  sibling of `load_vocab_tsv` (which returns `form`/`meaning` word dicts for
  quiz consumption, not a table-selection shape). Loads a bundled
  Word/Translation TSV via the existing `ensure_file`/`_resolve_tsv_path`
  local-then-remote resolution, with an optional `mo.ui.file()` upload
  override and an optional `<stem>_ru.<ext>`-vs-plain-filename switch for
  interfaces with a Russian variant. Returns `None` (never raises) when no
  candidate can be found, matching the contract every `created_with_eee`
  call site already hand-rolled around `ensure_file`/`pd.read_csv`.

## 1.7.3 - 2026-08-15
- `verb_meta`/`noun_meta`/`adj_meta`/`pron_meta` (`*_paradigm_drill_form`)
  are now optional (default `None`) instead of required keyword-only
  arguments. A caller that omits one now gets the full, unfiltered slot/case
  list for that word instead of `TypeError: missing 1 required keyword-only
  argument`. This closed a real gap: the parameter has been required since
  1.7.0, but a bug this same day showed 14 separate notebooks across 3
  courses had been written (or copy-pasted from an older template) without
  ever computing and passing it, crashing on first use. Reuses the existing
  `getattr(X_meta, "...", None) or <full list>` fallback already used by
  verb/adjective/pronoun. Adds one `*_meta_omitted_falls_back_to_full_*`
  regression test per POS type (`TestPronounParadigmDrillForm` is new --
  the other three already existed).
- Fix a latent noun-only gap in the same fallback machinery: `noun_meta`'s
  own fallback was `[]` (renders nothing) instead of `config.noun_cells`
  (full list, matching the other three POS types), and noun's `make_cap`/
  `slot_ok` additionally required `noun_meta is not None` to function at
  all -- unlike its siblings, this silently disabled answer-checking
  entirely whenever `noun_meta` was omitted, worse than a crash. Both fixed
  to match verb/adjective/pronoun's existing behavior.
- Fix `reset_paradigm_drill_state()` ("start over" button, shared by the
  noun/verb/adjective/pronoun paradigm-drill tests) resetting the word queue
  to its raw, unshuffled `vocab` order instead of a fresh `random.sample()`
  shuffle like the initial load does. Reported live: a verb test always
  showed words in table order after switching tense and pressing restart.
  Adds `TestResetParadigmDrillState.test_reshuffles_on_restart`. Extracted
  the shared `_shuffle()` helper (also used by the pre-existing
  `_shuffle_start`) instead of inlining `random.sample(vocab, len(vocab))`
  a second time.

## 1.7.2 - 2026-08-15
- Add `pronoun-{en,ru,el}.tsv` slot-name label files (24 rows each: Case x
  Number x Gender for Nom/Gen/Acc/Voc x Sing/Plur x Masc/Fem/Neut), reusing
  `adj-*.tsv`'s own verified label text for the matching grammatical
  combinations. `get_slot_templates(..., pos="pronoun")` has always routed
  through the same `pronoun-{lang}.tsv` lookup as every other pos, but the
  file itself never existed -- every lookup silently fell through to the
  English-only `_QUIZ_ADJ_GENDER`/`_QUIZ_ADJ_NUM` fallback, so
  `pronoun_slot_labels()` showed identical unlocalized labels ("Neut Sg:")
  in en/ru/el alike. Caught live in `ellinika_b/chapter_03`'s pronoun
  drill. Adds `TestPronounSlotLabelsLang` (mirrors the existing
  `TestAdjectiveSlotLabelsLang`) to cover en/ru/el localization plus the
  no-`eee_module`/raw-tag-backend fallback cases.
- Add an `all_forms_label` UI label (en/ru/el) and collapse
  `_gendered_slot_names()` to it whenever `active_slots` narrows to exactly
  one slot — an indeclinable word like κάτι/τίποτα has its entire tested
  paradigm in a single neuter-singular cell, so labeling that one field
  with its specific case/gender ("Nom. Sg. n.:") implied a fuller paradigm
  existed just off-screen. Adds `test_single_active_slot_collapses_to_
  all_forms_label`/`test_multiple_active_slots_unaffected` to
  `TestPronounSlotLabelsLang`.

## 1.7.1 - 2026-08-14
- Add `test4_heading`/`test4_done`/`pron_heading`/`select_pron`/
  `pron_not_found`/`pron_empty` UI labels (en/ru/el) — a 4th
  chapter-test-section slot alongside the existing `test1_heading`..
  `test3_heading`/`test1_done`..`test3_done` (nouns/verbs/adjectives), a
  drill-section title (`pron_heading`, matching `adj_heading`'s
  `**X test**` pattern), and the matching `select_*`/`*_not_found`/
  `*_empty` triple (mirroring `select_adjs`/`adjs_not_found`/`adj_empty`)
  for notebooks adding a dedicated pronoun test section. Distinct from the
  existing `pron_test_topic`/`pron_done` keys, which serve the generic
  `pos_selector`-driven example notebook.

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
