# Changelog

## 1.10.0 - 2026-08-24
- `GreekConfig` is now a frozen dataclass, so a course can no longer
  accidentally mutate the shared `MODERN_GREEK`/`ANCIENT_GREEK` singletons
  in place (which would silently affect every other course reusing them).
  Customize via `dataclasses.replace(MODERN_GREEK, ...)` to get a new,
  independent instance instead.
- `GreekConfig` gained two new opt-in fields, `nav_icons` and
  `show_prev_when_done` (both default `False`, matching every existing
  config's current behavior unchanged). The nine public quiz/drill
  functions that already accepted same-named `nav_icons`/
  `show_prev_when_done` keyword arguments (`paradigm_drill_widgets`,
  `word_drill_widgets`, `word_quiz_widgets`, `word_drill_form`,
  `word_quiz_form`, `noun_paradigm_drill_form`, `verb_paradigm_drill_form`,
  `adjective_paradigm_drill_form`, `pronoun_paradigm_drill_form`) now
  default those parameters to `None` and resolve from `self._cfg` when the
  caller doesn't pass an explicit value — an explicit `True`/`False` at the
  call site still always wins. Lets a course that wants the ◀/▶/↺ nav-icon
  treatment and done-screen Prev review everywhere set it once, on the
  `GreekConfig` it passes to `GreekUtils(..., config=...)`, instead of
  repeating both kwargs at every one of dozens of call sites across every
  chapter. Not exposed as a named config constant here — courses derive
  their own opted-in value via `dataclasses.replace(MODERN_GREEK,
  nav_icons=True, show_prev_when_done=True)` (or the same on
  `ANCIENT_GREEK`) at the point where they construct `GreekUtils`, since
  the feature itself is language-agnostic and this package shouldn't
  presume which specific course wants it. 10 new tests (one per function,
  proving the resolve-from-config path specifically, plus an explicit-
  override-wins case for `paradigm_drill_widgets`) — the full suite
  passing alone wouldn't have caught a config field silently not reaching
  one of the nine call sites, since every existing test already passes
  `nav_icons` explicitly. Full suite 1479/1479, `ruff check` clean.

## 1.9.1 - 2026-08-21
- `word_drill_form` now auto-advances to the next word immediately on a
  correct check (Check-button click *or* Enter), matching the paradigm-drill
  family's own "correct -> immediately advance, no separate Next click
  needed" behavior (`_paradigm_drill_form`'s `if ok: ... set_words(...)
  ...`) — previously every correct answer still required an extra manual
  Next click that the noun/verb/adjective/pronoun tests never needed.
  `dia_reactive`'s `enter_pressed` is a counter that never auto-resets
  (unlike `mo.ui.button.value`, which marimo itself resets to `False` once
  a click is consumed), which initially looked like a double-fire risk on
  a later state-triggered re-render — but `word_drill_widgets` rebuilds
  `write_input` fresh on every `cv`/`restore_entry` change, and marimo's
  dependency graph guarantees that rebuild runs before this code re-reads
  it on the very re-run advancing triggers, so the already-empty input
  blocks re-triggering regardless of the stale `enter_pressed` count.
  Confirmed empirically with an isolated probe notebook mirroring this
  exact shape, not just reasoned about. Skipped while browsing forward
  through answered history (`future` non-empty), matching how the Next
  button already treats that case separately. 8 new tests (including one
  specifically for the Enter path landing on the correct word exactly
  once), verified against the real live kernel too (not just mocked unit
  tests) — a correct answer without its expected trailing punctuation
  advanced automatically to the next phrase with the right score/history,
  in one call. Full suite 1394/1394, `ruff check` clean.
- Fixed `load_ga_config()`'s docstring, which blanket-instructed gitignoring
  `ga.json` — correct for the plain local-file case this function reads
  directly, but wrong for the actual production pattern real course
  notebooks use (`ConfigStore.from_url`/`from_file_or_url`, which *fetch*
  `ga.json` from the repo's own raw-content URL when deployed as a WASM
  export, requiring the file to be committed). A GA measurement ID isn't a
  secret, so committing it for that case is correct, not an oversight — the
  docstring just never said so.
- Added 10 new `ui-{en,ru,el}.tsv` keys (`phrases_heading`, `select_phrases`,
  `phrases_empty`, `phrases_not_found`, `phrases_done`, `phrase_heading`,
  `phrases_too_few`, `phrase_mode_label`, `quiz_mode_choice`, `quiz_mode_type`)
  for a new phrase-recall quiz type in course notebooks — the same
  `word_quiz_widgets`/`word_quiz_form` (multiple-choice) and
  `word_drill_widgets`/`word_drill_form` (type-the-answer) mechanisms already
  used for Odyssey's word-form quizzes, now also wired to a course's own
  "Useful Phrases" vocabulary via `vocab_table`/`load_vocab_table`, with a
  mode toggle between the two. Also fixed a stale `__init__.py.__version__`
  (said 1.8.1, one release behind pyproject.toml's 1.9.0) while bumping this
  release.
- Fixed `diacritics_text()`/`word_drill_widgets`/`word_write_question`
  hardcoding the full polytonic (Ancient Greek) diacritics mark set —
  breathing marks, circumflex, iota subscript — with no way to get the
  Modern Greek monotonic set (acute accent + diaeresis only) instead, unlike
  its sibling `make_paradigm_form`, which already had exactly this
  `polytonic` toggle sourced from `GreekConfig.polytonic`
  (`MODERN_GREEK`=`False`, `ANCIENT_GREEK`=`True`). Found live testing the
  new phrase-drill's type-the-answer mode on a Modern Greek course, where
  the full Ancient Greek mark bar made no sense. `diacritics_text()` gained
  a `polytonic: bool = True` parameter (default preserves every existing
  caller's behavior unchanged); `GreekUtils.diacritics_text()` defaults it
  from `self._cfg.polytonic` when not given explicitly, same convention as
  `make_paradigm_form`'s own config-driven default — so `word_drill_widgets`
  (which already calls the method with no explicit `polytonic`) picks up
  the right mark set automatically, with no changes to that function itself.
  Moved the `MONOTONIC_MARKS` filter into the shared `_DIACRITIC_CORE_JS`
  prefix (previously duplicated inside `_PARA_ESM` alone) so both widgets'
  JS use the identical filter instead of two copies.
- Fixed `greek_compare()` (and therefore every `word_drill_form`/`_ci`
  answer check) requiring exact punctuation and whitespace to match —
  harmless for the single grammatical forms it was originally designed to
  compare (no embedded punctuation or spaces in a bare declined/conjugated
  form), but wrong for the new phrase-drill mode, where a student typing the
  entirely correct phrase without its trailing "?"/";"/"..." or with an
  extra space was marked wrong. Found in the same live test as the
  diacritics fix above. `greek_compare()` now treats any run of punctuation
  as a word separator (replaced with a space) and collapses whitespace runs,
  comparing only the resulting word sequence — a no-op for a plain
  single-word form (nothing to strip), verified against all 13 pre-existing
  `greek_compare` tests still passing unchanged, plus 7 new tests for the
  phrase case. 12 new tests total this entry (7 `greek_compare`, 5
  `diacritics_text`/`GreekUtils.diacritics_text`/`word_write_question`
  polytonic-threading). Full suite 1386/1386, `ruff check` clean.
- Fixed `vocab_table()` truncating long entries (e.g. full sentences in the
  new phrase-quiz table) instead of wrapping them — `mo.ui.table` truncates
  any column by default unless told to wrap it via its own
  `wrapped_columns: list[str] | None` parameter, which `vocab_table()` never
  passed. Fixed by passing `wrapped_columns=list(df.columns)` — every
  column, derived from the actual DataFrame rather than hardcoded as
  `["Word", "Translation"]`, since `mo.ui.table` raises `ValueError` if a
  named column doesn't exist and `vocab_table` is also used with an
  additional `Type` column elsewhere. Found live-testing the phrase-quiz
  selection table with a full-sentence phrase. 1 new test asserting all
  columns of a 3-column table are wrapped, not just the first two. Full
  suite 1395/1395, `ruff check` clean.
- Added `word_drill_check_button` and an opt-in `nav_icons` parameter to
  `word_drill_widgets`/`word_drill_form`/`word_drill_display`, for a
  `word_drill_form` caller that wants the same "warn"-colored (orange)
  Check button `dirty_check_button` already gives paradigm-drill exercises,
  plus bare ◀/▶ Prev/Next buttons flanking Check instead of localized
  text-labeled ones. Both default off/absent, so every existing caller
  (Odyssey's word-form quizzes, still using the plain `check_btn`
  `word_drill_widgets` returns) is unaffected.
  `word_drill_check_button(dia_reactive, checked, *, label="Check")` is the
  single-field analogue of `dirty_check_button`: built in its own cell
  (same reason `dirty_check_button` is kept out of `paradigm_drill_widgets`
  — it needs `dia_reactive` for live-as-you-type recoloring, and folding it
  into `word_drill_widgets` would rebuild `write_input` from scratch on
  every keystroke). `checked` is the exact text last submitted via
  Check/Enter for the current word; `word_drill_form` now accepts an
  optional `get_checked`/`set_checked` state pair it keeps in lockstep with
  `restore_entry` at every transition (reset together on a fresh word,
  restored together when browsing Prev/Next history) so the button always
  compares against "what was checked for the word on screen."
  Found and fixed a real bug building this: a check button that recolors
  live necessarily rebuilds (resetting its own transient click value)
  the instant a check attempt updates the `checked` state it's colored
  from — which was erasing `word_drill_display`'s own `check_btn.value`-based
  feedback trigger before a wrong answer's feedback ever rendered (confirmed
  live: a real wrong-answer Check click showed no feedback at all, not even
  briefly, until fixed). Fixed by giving `word_drill_display` its own
  optional `checked` parameter, treating `checked == typed` the same as a
  fresh click for showing feedback — mirroring how `_paradigm_drill_form`'s
  own feedback decision already reads persisted `cap` state rather than the
  transient check-button value, for exactly this reason. `checked=None`
  (the default) leaves existing callers byte-for-byte unaffected.
  `nav_icons=True` also hides (rather than greys out) whichever of
  Prev/Next is at a history boundary, matching `eee_footer`'s own ◀/▶
  convention (a spacer instead of a disabled link). Found and fixed a
  second real bug here too: a real `mo.ui.button` has no readable
  `.disabled` after construction (only an internal frontend arg,
  confirmed by reading marimo's own `input.py` — `args={"disabled":
  disabled, ...}`, no `self.disabled` anywhere) — the first attempt at
  this read `prev_btn.disabled`/`next_btn.disabled` back off the
  already-built button objects, which crashed the live notebook with
  `AttributeError: 'button' object has no attribute 'disabled'` on the
  very first real click, even though the *entire* test suite passed,
  because the test double happened to store `disabled` as a plain
  instance attribute mirroring the constructor kwarg — a stub being
  looser than the real API it stands in for, silently. Fixed by adding
  explicit `prev_disabled`/`next_disabled` parameters to
  `word_drill_display` instead, which `word_drill_form` computes itself
  (`len(history) == 0` for `prev_disabled`, mirroring the exact condition
  `_make_nav_buttons` already used to build the button) rather than
  trying to read state back off a widget that never exposed it. 25 new
  tests (6 `word_drill_check_button`, 1 `word_drill_widgets` `nav_icons`,
  8 `word_drill_display` `nav_icons`/`checked`/hide-when-disabled, 10
  `word_drill_form` `get_checked`/`set_checked`/`nav_icons` transitions).
  Full suite 1420/1420, `ruff check` clean. Verified live end-to-end:
  dirty-orange while typing, neutral once the text matches what was last
  checked (right or wrong), wrong-answer feedback persists, correct-answer
  auto-advance unaffected, ◀/▶ flank Check and ◀ is genuinely absent (not
  just disabled) on the first phrase, reappearing once history exists.
- Fixed `nav_icons=True`'s restart button showing a bare ▶ (identical to
  "skip forward") once a drill reaches its done screen, contradicting the
  done-screen's own "press «Again»" callout text right next to it. Found by
  driving a full 15-phrase forward/backward/restart cycle live through
  marimo-pair (a fork agent, not just unit tests) at the user's request
  after the earlier `.disabled` incident — the backward/forward history
  walk itself turned out clean (Prev hides/reappears exactly at
  `history==0` in both directions, including the history→future seam), but
  this confirmed a second real issue: `_make_nav_buttons`'s `nav_icons`
  branch used a fixed "▶"/"◀" pair with no `done`-awareness at all, unlike
  its own text-label branch (`nav_again_label` vs `nav_next_label`). Now
  uses "↺" once done — the same restart glyph `make_renew_button` already
  uses elsewhere in this file, so there's no third icon convention to
  learn. 1 new test. Full suite 1421/1421, `ruff check` clean.
  Also confirmed the same walk-through: `_quiz_done_stop` (shared by
  `word_drill_display`/`word_quiz_form`/`stanza_match_form`/
  `translation_presence_form`) never received `prev_btn` at all, so Prev
  was unconditionally absent on every done screen for every quiz type —
  pre-existing, not introduced by `nav_icons`. Given the choice between
  leaving it, fixing it for every quiz type, or fixing it for just the one
  caller that asked, added it as opt-in: `_quiz_done_stop` gained an
  optional `prev_btn` parameter (rendered in an `mo.hstack` alongside
  `next_btn` only when *both* are given — a lone `next_btn`, every existing
  caller's exact shape today, still appends bare, unwrapped, preserving
  `content[-1] is next_btn`), and `word_drill_display`/`word_drill_form`
  gained `show_prev_when_done: bool = False` to opt into passing their own
  `prev_btn` through. Needed no new state-machine work — `_handle_prev`/
  `_make_future_entry` already handled `cv=None` gracefully (they just
  never had a visible button to trigger it from at the done screen).
  4 new tests (2 `_quiz_done_stop`, 2 `word_drill_display`). Full suite
  1425/1425, `ruff check` clean. Verified live end-to-end via marimo-pair
  (engineering the done state directly rather than 15 real clicks, since
  the forward/backward walk itself was already separately verified): ◀
  and ↺ both render at 15/15 done, clicking ◀ correctly reviews the last
  answered word (history 15→14, future 0→1, score 15/15→14/14, restore
  populated, 3-button row with ▶ not ↺ since we're not done anymore),
  clicking ▶ returns cleanly to the identical done screen, and ↺ from
  there still restarts correctly (fresh word, history/future/score all
  reset, Prev hidden again).
- Extended `nav_icons` (and its hide-at-history-boundary behavior) from
  `word_drill_widgets`/`word_drill_form` to `word_quiz_widgets`/
  `word_quiz_form` too, so a multiple-choice quiz can look and behave the
  same as its type-the-answer sibling. `word_quiz_form` needed no new
  reordering logic — its row was already Prev-before-Next (there's no
  Check button to flank, since selecting a radio option scores
  immediately) — just hiding Prev at the start of history, reusing
  `_nav_row`'s own existing "drop `None` entries" mechanic (already how it
  omits an unused `renew_btn`) rather than adding a new mechanism: pass
  `None` instead of `prev_btn` when it should hide, no changes to the
  shared `_nav_row` helper itself (still used unmodified by
  `stanza_match_form`/`translation_presence_form`). The done-screen
  "▶"-vs-"↺" distinction came for free — `next_btn`'s label is built by
  the already-fixed `_make_nav_buttons`. 6 new tests. Full suite
  1430/1430, `ruff check` clean. Verified live: ◀ absent on question 1,
  both ◀/▶ present on question 2 in Multiple Choice mode.
- Changed `word_quiz_form`'s Next button to always advance, whether or not
  a radio option is selected — previously clicking Next with nothing
  picked just re-rendered the same question in place (a deliberate,
  tested, but inconsistent design: `word_drill_form`'s own Next has never
  required typing anything first, an empty submit already scores wrong
  and advances). This is a **default behavior change**, not opt-in like
  every other fix in this release — confirmed explicitly with the user,
  who chose it over scoping it to one caller, so it applies to every
  existing `word_quiz_form` caller (16+ Odyssey/Palaestra lessons, not
  just the phrase quiz that prompted the question). `stanza_match_form`/
  `translation_presence_form` share a *different* helper
  (`_handle_quiz_next`) with the identical "require a selection" pattern —
  intentionally NOT touched here, since only `word_quiz_form` was in
  scope of what was actually asked. An unanswered question now scores
  wrong (`answer_radio.value is None` never equals `cv[form_key]`, no
  special-casing needed) and is recorded in history as
  `{"answer": None, "correct": False}`, reviewable via Prev exactly like
  any other answered word. 2 new tests replace the one that asserted the
  old behavior; 4 more existing tests updated (they used
  `next_v=1, radio=value=None` merely as a way to reach the display
  path without a real click — now they just don't click Next at all,
  which is both simpler and no longer coincidentally relies on the
  behavior being changed here). Full suite 1431/1431, `ruff check` clean.
- `nav_icons=True`'s ◀/▶ now decorate the localized Prev/Next(/Again) text
  instead of replacing it (``"◀ Prev"``, ``"Next ▶"`` — arrow pointing in
  the direction of travel; done screen's restart gets ``"↺ Again"``, icon
  *before* text there, matching `make_renew_button`'s own convention).
  Also fixed `word_quiz_form` so Prev/Next stay first/last in the row even
  with `renew_btn` present in icon mode — previously the row order was
  fixed at `[prev_btn, next_btn, renew_btn]` regardless of `nav_icons`, so
  a caller passing `renew_btn` would end up with Next in the middle, not
  last. `word_drill_display`'s own row was already `[prev_btn, check_btn,
  next_btn]` (Prev/Next already first/last, Check in between) — no change
  needed there. Default (non-icon) ordering is untouched either way — this
  reorder only applies when `nav_icons=True`. 5 new/updated tests
  (4 label-content fixes across `word_drill_widgets`/`word_quiz_widgets`,
  1 new `renew_btn`-ordering test). Full suite 1432/1432, `ruff check`
  clean. Verified live: "◀ Prev" / "Check" / "Next ▶" all render with
  their labels, in the right order, through a full type-answer cycle.
- Extended `nav_icons` to the paradigm-drill family too (`paradigm_drill_widgets`
  and `verb_paradigm_drill_form`/`noun_paradigm_drill_form`/
  `adjective_paradigm_drill_form`/`pronoun_paradigm_drill_form`, the shared
  engine behind noun/verb/adjective/pronoun "pos tests") — same idea as
  `word_drill`/`word_quiz`, but genuinely different mechanics: this family
  builds its own Prev/Next/Restart directly (never went through
  `_make_nav_buttons`), and Restart is its own always-separate button
  rather than Next relabeling itself when done. `_paradigm_drill_form`'s
  row reorders to `[prev_btn, check_btn, nxt_btn]` (was fixed at
  `[check_btn, prev_btn, nxt_btn]`); Prev's hide condition is computed from
  `hist` itself, matching the exact condition `paradigm_drill_widgets`
  used to build it disabled (not read back off the button object — same
  `.disabled`-doesn't-exist reasoning as before). Restart gets
  `"↺ {text}"` for free from `paradigm_drill_widgets`, so
  `_paradigm_drill_form` doesn't need `nav_icons` for that part, only for
  the reordering/hiding.
  **Found and fixed a real, pre-existing, unrelated inconsistency while
  wiring this up**: the `next_label`/`prev_label`/`restart_label` TSV keys
  (distinct from `nav_next_label`/`nav_prev_label`/`nav_again_label`,
  which this whole `nav_icons` feature is built on) already had ◂/▸/↺
  baked into their *English* values only (`"Next ▸"`, `"◂ Prev"`,
  `"↺ Start over"` — ru/el plain, and the sibling `nav_*_label` keys
  introduced in the very same commit also plain) — an accidental
  inconsistency from v1.9.0's original EN-translation pass, not a
  deliberate design. Left as-is, this would have doubled up with
  `nav_icons`'s own decoration for English paradigm drills specifically
  (`"Next ▸ ▶"`). Fixed by making `ui-en.tsv` plain here too, matching
  every other language and every other nav-label key; `nav_icons=True`
  is now the only source of icons anywhere in the UI, uniformly across
  ru/en/el.
  **Also compared directly against `word_drill`/`word_quiz` at the user's
  request and found a real behavioral gap, not just cosmetic**:
  `paradigm_drill_widgets` originally disabled `nxt_btn` at
  `remaining_len <= 1` (Next unusable with only one word queued at all) —
  unlike `word_drill_widgets`' own `next_btn`, never disabled by remaining
  count. Confirmed with the user and changed to `remaining_len < 1` (a
  bound the current-word-inclusive count never actually reaches in
  practice, so effectively "never disabled"): the underlying handler
  already tolerated moving the sole word straight to "done" via Next with
  no special-casing needed (this family has no per-word score to get
  wrong on skip, unlike `word_drill_form`'s own Next) — it just needed the
  disabled-arg loosened. `_paradigm_drill_form`'s own nxt-hide condition
  became permanently unreachable once the early "if not words" return
  guarantees `words` is non-empty by then, so it was removed rather than
  left as dead code — Next is now never hidden here either, mirroring
  `word_drill`/`word_quiz` exactly: only Prev ever hides, Next never does.
  13 new/updated tests total across both rounds (11 net new; 4 widget-level
  label tests — one being the existing EN-TSV test updated for the
  plain-text fix rather than new; 4 on the verb sibling covering the full
  row/hide battery, one of which was updated again for the
  `remaining_len` fix; 1 smoke test each on noun/adjective/pronoun; 2 more
  for the `remaining_len` threshold itself — one updating a pre-existing
  test, one new). Full suite 1443/1443, `ruff check` clean. Verified live on the noun
  test, both rounds: "◀ Prev" appears once history exists and "Next"
  hides on the last word (first round); then, with only 1 word selected
  from the start, "Next ▶" is genuinely clickable and correctly advances
  straight to the done screen, "↺ Start over" rendering correctly with a
  single icon (second round, after the `remaining_len` fix).
- Consolidated the `nav_icons=True` button-row logic — Prev first (hidden
  if disabled), Next last (hidden if disabled), whatever's in between
  (`check_btn` for `word_drill_display`/`_paradigm_drill_form`,
  `renew_btn` for `word_quiz_form`) unchanged — from three near-identical
  inline copies into one shared `_icon_nav_row` helper, at the user's
  request after comparing the two families' logic directly. Returns a
  plain widget list rather than an already-built `mo.hstack`, since each
  caller wraps it with its own `justify` value (`"start"` for word_drill/
  word_quiz, `"end"` for paradigm-drill — an existing difference this
  consolidation doesn't touch). Purely mechanical: every existing test
  passed unchanged, confirming behavior is identical to the three
  separate copies it replaces. 6 new direct unit tests for the helper
  itself (prev/next hiding independently, multiple middle widgets kept in
  order, a `None` middle widget dropped the same way `renew_btn=None`
  already needed, zero middle widgets). Full suite 1449/1449, `ruff check`
  clean. Verified live: the phrase quiz's "Type the answer" mode still
  renders "Check"/"Next ▶" identically to before the refactor.
- Consolidated the two families' *done-screen* rendering too, at the
  user's request after comparing pos-test vs. phrase-test done screens
  directly and asking for one shared function. `_quiz_done_stop` (used by
  `word_drill_display`/`word_quiz_form`/`stanza_match_form`/
  `translation_presence_form`) now delegates its actual content-building
  to a new `_drill_done_content(message, *, score_line=None,
  buttons=None)` — a success callout plus an optional score line plus a
  button row (bare if one button, hstacked if more, omitted if none) —
  and `_paradigm_drill_form`'s own done-block, previously a hand-rolled
  `mo.vstack`, now calls the same function directly (its done-check is
  the function's first early-return rather than a mid-function halt, so
  it returns the content instead of wrapping it in `mo.stop` the way
  `_quiz_done_stop` does). A literal single function driving *both*
  families' Next-button click-handling turned out not to be sound — the
  two track fundamentally different state (single-radio answer + running
  correct/total score + bidirectional history/future replay stacks, vs.
  multi-field form + no per-word score on Next at all + one-directional
  history only) — so the click-handling itself stays separate; only the
  done-*screen* (message/score-line/buttons) is genuinely shared now,
  confirmed as the right scope with the user before implementing.
  New `show_prev_when_done` parameter on `_paradigm_drill_form` and all
  four public wrappers (`verb_`/`noun_`/`adjective_`/
  `pronoun_paradigm_drill_form`) — same name and convention as
  `word_drill_display`'s own flag — lets a finished pos-test round still
  be reviewed via Prev instead of only restart/retry, closing a real gap:
  pos-tests' Prev was previously unreachable from the done screen at all,
  not just hidden — the function returned early on `if not words` before
  `prev_btn.value` was ever checked, even though the Prev handler itself
  only ever depended on `hist`, never on `cv`/`form`/whether `words` was
  empty. Moved the Prev-click check to run before the done-screen
  early-return (harmless for the in-progress case, since restart/retry
  still take priority and nothing about Prev's own logic changes) so
  Prev now actually works from done, not just renders there. Default
  `False` — every existing caller's restart-only (or restart+retry) done
  screen is unchanged unless it opts in.
  17 new tests: 9 directly on `_drill_done_content` (message-only,
  message+score, single button bare, `None` entries filtered before the
  bare-vs-hstack check, multiple buttons hstacked in order, no buttons
  omits the row); 5 on `show_prev_when_done` in `TestVerbParadigmDrillForm`
  (hidden by default, shown with history when opted in, hidden with no
  history even when opted in, shown alongside retry_btn when both apply,
  and the functional case — clicking Prev from the done screen actually
  restores the last word); 3 one-line smoke tests confirming the
  parameter threads through on the noun/adjective/pronoun siblings. Every
  pre-existing `_quiz_done_stop`/`_paradigm_drill_form` done-state test
  passed unchanged, confirming the refactor is behavior-preserving. Full
  suite 1466/1466, `ruff check` clean. Verified live on the noun test
  with a single noun selected: done screen now shows "◀ Prev" alongside
  "↺ Start over", and clicking it correctly returns to the question
  (empty fields, since the word was skipped unscored, never answered);
  re-verified the phrase quiz's own done screen unchanged ("🎉 All words
  done! Press «Again» to repeat.", "Correct: 0 / 1", "◀ Prev" / "↺ Again").
- `paradigm_drill_widgets`' restart button now defaults its label from
  `nav_again_label` instead of the separate `restart_label` key, at the
  user's request after noticing pos-tests showed "↺ Start over" while
  phrase-tests showed "↺ Again" for what is the identical restart action —
  an unintentional wording gap between two TSV keys, not a deliberate
  distinction (confirmed with the user before merging them). `restart_label`
  is now unused (its only consumer was this one default-fallback line) and
  was removed from all 3 `ui-{en,ru,el}.tsv` files. Also rewrote
  `test1_done`/`test2_done`/`test3_done`/`test4_done` (the shared
  eee-project-level done-messages pos-tests use across 13 course notebooks,
  distinct from `quiz_done_message` used by phrase-tests) in all 3 languages
  to match `quiz_done_message`'s own "🎉 ... Press «Again» to repeat."
  template, keeping each key's own part-of-speech word (nouns/verbs/
  adjectives/pronouns) rather than genericizing to "words". No test-count
  change (existing tests' expected label text updated, none added/removed):
  full suite 1466/1466, `ruff check` clean. Verified live: the noun test's
  done screen now reads "🎉 All nouns done! Press «Again» to repeat." with
  "↺ Again", matching the phrase quiz's phrasing exactly.
- Added a "forms of a Modern Greek verb" example to `docs/api-patterns.md`'s
  Pattern B section (previously `grc`-only): `get_slot_templates` +
  `inflect_slot` for the full paradigm, `inflect()` directly for the aorist
  specifically — which isn't its own UD `Tense` value in Modern Greek (unlike
  Ancient Greek's literal `"Aor"`), it's `Tense=Past` + `Aspect=Perf`, a
  non-obvious mapping worth calling out explicitly. Verified against the
  real backend rather than hand-typed (λύω has 104 verb slots; aorist active
  1sg → `έλυσα`).
- Moved `docs/examples.md` to `examples/README.md` (`git mv`), turned the
  file-listing table into real relative links (render correctly on all 3
  hosts' directory pages), and fixed the one cross-reference in root
  `README.md` — which also had a stale "13 runnable scripts" count, one
  behind the real total of 14.
- Fixed `greek_exercise_notebook.py` showing duplicate navigation chrome
  once deployed: its own internal `eee_topbar`/`eee_footer` calls, stacked
  underneath the WASM-export deploy shell's own topbar/footer (added at
  publish time, outside version control on the `pages` branch, identical
  across all 6 live demos) — two "back" links to two different
  destinations, two source-footers. Removed the internal calls, and the
  API-reference table row describing them (no longer true). This notebook's
  own content now starts with just its title/description like the other 5
  deployed notebooks; the deploy shell alone carries page-level navigation.
  Confirmed via live DOM inspection after a local re-export: `#eee-topbar`/
  `#eee-footer` both absent.
- Brought `modern_greek_drill_notebook.py`'s paradigm-drill calls up to the
  same look and feel as `ellinika_b/chapter_08`: switched `done_message`
  from its own separate `verb_done`/`noun_done`/`adj_done`/`pron_done` TSV
  keys (plain "Done — every verb drilled!", no emoji) to the shared
  `test1_done`..`test4_done` keys, and added `nav_icons=True,
  show_prev_when_done=True`. Removed the now-dead `verb_done`/`noun_done`/
  `adj_done`/`pron_done` keys (confirmed no other consumer) from all 3
  TSVs.
- Fixed a stale `codeberg.org/EEE-project/eee` link (pre-rename repo name;
  redirects correctly, but inconsistent with every other reference) to
  `EEE-project/eee-project` in the 3 notebooks that had it.
- Investigated a reported "Couldn't load notebook" failure on the live
  `greek/` demo — could not reproduce after two full loads (~30-40s each,
  well under the deploy shell's 90s timeout), no console errors, no failed
  requests. `greek_notebook.py` registers 4 backends at once (modern-greek,
  ancient-greek, unimorph×2 languages) — the heaviest of the 6 demos to
  boot — most likely a transient slow-network/cold-CDN load rather than a
  code defect. Full suite 1466/1466, `marimo check`/`ruff check` clean on
  every touched file.
- Pulled the live demos' shared WASM deploy shell (loading animation, topbar
  with back-link/GA, source footer, error/retry state — iframes the actual
  notebook) into version control as `examples/deploy/shell_template.html`.
  Previously it existed only as 6 hand-duplicated copies on the `pages`
  branch, outside `main` entirely, differing from each other only in one
  title string repeated at 4 spots — confirmed byte-identical otherwise by
  diffing all 6 pairwise. Added `examples/deploy/build_shell.py` (stdlib
  only) to fill in the title and split a raw `marimo export html-wasm`
  output into the deployed two-file shape: its own `index.html` becomes
  `notebook.html`, the filled-in template becomes the new `index.html`.
  Wired into all 6 `export-*` Makefile targets, so `make export-drill` (etc.)
  now produces `dist/<name>/` exactly as it appears on the `pages` branch,
  with no manual shell-copying step. Verified by generating `drill` and
  `exercise` (the latter to exercise the `&` in "Exercise & Quiz Demo")
  through the new pipeline and diffing each against its real deployed
  `index.html`: byte-identical both times.
- `/simplify` pass over the accumulated diff (4 parallel review agents —
  reuse, simplification, efficiency, altitude): reuse and efficiency came
  back clean; simplification and altitude found 3 real issues, all fixed.
  `word_drill_form`'s auto-advance-on-correct-check block and its Next-
  button "normal advance" block had become two independent copies of the
  same 6-statement "record this answer, advance to the next word" sequence
  (differing only in whether correctness was hardcoded `True` or computed)
  — extracted into a shared `_advance(typed, ok)` closure, called from
  both. `_icon_nav_row` carried a `next_disabled` parameter added purely
  for symmetry with `prev_disabled` — its own docstring already admitted
  "nothing passes it today" — with zero real callers across
  `_paradigm_drill_form`/`word_drill_display`/`word_quiz_form`, only two
  unit tests that existed solely to exercise it; removed from
  `_icon_nav_row` and `word_drill_display` (and the two tests that covered
  only it) rather than keep speculative flexibility nothing uses.
  Separately, the ◀/▶/↺ icon-decoration convention (which glyph goes on
  which side of the text) was hand-written independently in both
  `_make_nav_buttons` and `paradigm_drill_widgets`, even though this same
  round already consolidated the *adjacent* row-arrangement logic into one
  shared `_icon_nav_row` — the kind of two-places-encode-the-same-rule gap
  that had already caused one real bug earlier in this round (the TSV/
  `nav_icons` double-decoration fix). Extracted a new `_icon_decorate(text,
  icon, *, before)` helper, used by both. All three fixes are pure
  refactors verified against the existing test suite (no new tests needed
  — output strings are unchanged, confirmed by construction and by every
  pre-existing label-text assertion still passing): full suite 1469/1469
  (2 fewer than before — the two `next_disabled`-only tests removed, none
  else touched), `ruff check`/`marimo check` clean.

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
