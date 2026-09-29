# AGENTS.md

Guidance for AI coding agents (and humans) changing `eee-project`'s own
source. For how to *use* the library from a notebook, see
[docs/api-patterns.md](docs/api-patterns.md) — that file is the primary
reference for notebook authors and is checked before source, per the parent
workspace's own CLAUDE.md ("EEE API Reference Workflow").

## Development

```bash
make test      # run all tests (quiet)
make test-v    # run all tests (verbose)
make check     # ruff, curated rule set — see [tool.ruff.lint] in pyproject.toml
```

## Before committing a change to `src/eee_project/`

1. **Tests** — a passing suite isn't enough on its own if it was already
   passing before the change; that only proves nothing broke, not that new
   behavior is covered. Add a test that specifically exercises the new/fixed
   code path (a regression would need to fail it). `tests/test_notebook_utils.py`
   (for `notebook_utils.py`'s own widget/`GreekUtils` surface) and
   `tests/test_content.py` (for `content.py`'s non-widget helpers) share the
   same style: one class per function, one test per behavior. **Exception:**
   JS living inside an anywidget's `_esm` string — pytest can't reach it at
   all (no JS test runner in this repo); see the live-kernel-testing
   Convention below, which is the only check that exists for that code.
2. **`docs/api-patterns.md`** — any new public method or parameter on
   `GreekUtils`/`notebook_utils.py` needs a worked usage example here, not
   just a docstring or a passing mention elsewhere in the file.
3. **Version bump** — `pyproject.toml` and `src/eee_project/__init__.py`'s
   `__version__`, kept in sync. Patch for a fix, minor for a new
   capability/backend, major for a breaking change.
4. **`CHANGELOG.md`** — one entry per version bump, newest on top. Match the
   existing entries' level of detail: what changed, why (the bug/gap that
   motivated it, not just the mechanical diff), and the verification state
   (test count, `ruff check` status).
5. **Lint** — `make check` on changed files.

`README.md` deliberately carries no changelog section of its own — one
existed inline through v1.0.0 but was removed in the same commit as the
PyPI-packaging README rework (`30fa087`) for being too noisy there. Don't
re-add one to `README.md`; `CHANGELOG.md` (a separate top-level file,
introduced shortly after `30fa087`) is where per-version detail lives now —
`docs/api-patterns.md` stays the source of truth for current capability
(what a function does today), not for change history (what changed and why).

## Conventions

- **Widget creation and conditional display belong in separate cells.** A
  `mo.ui.*` widget recreated inside a cell that also depends on unrelated
  reactive state (e.g. a part-of-speech switcher) resets to its
  construction-time default on every rerun of that cell — confirmed
  empirically. Build the widget in a cell with no dependency on the
  switching state; display it conditionally in a separate cell that only
  *references* the already-built widget object, never reconstructs it. See
  `examples/greek_exercise_notebook.py`'s `article_toggle_ag`/
  `article_toggle_mg` cells for the pattern.
- **Never call a backend's `.paradigm()` directly, and never key off a
  backend-internal tag name** (e.g. `paradigm(word, pos)["ADV"]`). Always go
  through `get_slot_templates()` + `inflect_slot()` — see the parent
  workspace CLAUDE.md's tagging rule.
- Test any notebook change with the `marimo-pair` skill against a real
  running kernel before considering it done — reading the `.py` source is
  not equivalent to seeing it actually render and behave correctly. For JS
  inside an anywidget `_esm` string (e.g. `_ParadigmFormWidget`'s `render()`),
  this live check is not optional polish — it's the *only* verification
  that exists, since pytest never executes that code at all. A DOM-level
  behavior (e.g. focus state) needs a real browser: `document.activeElement`
  in the console/`javascript_tool`, not just a passing test run. If clicking
  something freezes claude-in-chrome's screenshot capture (native `<select>`
  dropdowns are known to do this — the page itself is fine, only
  `Page.captureScreenshot` hangs), switch to JS-only interaction
  (`javascript_exec` for DOM queries/events) rather than retrying screenshots.

## Commit messages

One commit per version bump (`vX.Y.Z: ...`), squashed from whatever WIP
happened during development — not one commit per change. Short single-line
subject, no body, no attribution trailer. Full detail lives in
`docs/api-patterns.md`, not the commit message itself.
