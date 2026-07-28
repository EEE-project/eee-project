"""Marimo notebook helper utilities for EEE language exercises.

Navigation
----------
eee_topbar(mo, back_url, lang, titles)  — sticky topbar with back link + EEE badge
eee_footer(mo, lang)                    — source footer bar (codeberg.org/EEE-project)
diacritics_text(mo, *, placeholder, label) — polytonic diacritics bar + text input

Both functions return a mo.Html() object and must be used as the **last expression**
in a marimo cell (no trailing ``return``), otherwise the output is silently dropped.

Greek comparison utilities
---------------------------
strip_diacritics(s)            — remove polytonic diacritical marks
greek_compare(a, b)            — unified comparison (case + diacritics flags)

GreekUtils (exercise widgets)
------------------------------
Backend-agnostic widget driver for noun, verb, adjective, and item-drill quiz cells.

Usage::

    import eee_project as eee
    from eee_project import GreekUtils, ANCIENT_GREEK
    import marimo as mo

    ag = AncientGreekBackend(...)
    eee.register_backend("grc", ag, backend="ancient-greek")
    gu = GreekUtils(ag, mo, eee_module=eee, config=ANCIENT_GREEK)

    # batch slot drill (show all items at once)
    inputs_2d, rows = gu.make_item_drill_rows(items, ["sg", "pl"], ...)
    feedback = gu.check_item_drill(items, inputs_2d, ["sg", "pl"], strict=False)

    # vocab quiz (multiple-choice)
    radio, word = gu.word_quiz_question(cv(), all_words, "ru", random)
    fb = gu.word_quiz_feedback(radio, word, score, "ru")

    # vocab quiz (write the word)
    path = gu.ensure_file("words.tsv", nb_dir=Path(__file__).parent, remote_base=REMOTE_URL)
    words = gu.load_vocab_tsv("verbs.tsv", "nouns.tsv", nb_dir=Path(__file__).parent, remote_base=REMOTE_URL)
    inp = gu.word_write_question(cv(), "ru")
    # feedback: check inp.value against cv()["form"] on your own Check-button
    # gate (see examples/greek_exercise_notebook.py); or for a fully-managed
    # gated write-drill use word_drill_widgets() + word_drill_form() instead
"""

from __future__ import annotations

import csv
import functools
import importlib.resources
import io
import random as _random
import re as _re
import unicodedata as _unicodedata
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from eee_project._grammar_fmt import fmt_ud_feats, _FMT_CASE
from eee_project._registry import register_backend, set_chain
from eee_project._slot_template import SlotTemplate

_INC: Any = lambda v: (v or 0) + 1  # shared on_click incrementer for mo.ui.button


# ═══════════════════════════════════════════════ navigation ══

_TOPBAR_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;700;800&display=swap');
#eee-topbar {
  position: sticky; top: 0; z-index: 100;
  height: 48px; background: #f5f5f5;
  border-bottom: 2px solid #003d82;
  display: flex; align-items: center;
  padding: 0 12px; gap: 10px;
  margin: -16px -16px 16px -16px;
  font-family: Syne, sans-serif;
}
#eee-topbar .tb-back {
  font-size: 15px; font-weight: 700; letter-spacing: 0.02em;
  color: #003d82; text-decoration: none;
  padding: 4px 6px; flex: 1;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
#eee-topbar .tb-badge {
  font-family: "DM Mono", monospace; font-size: 12px; font-weight: 700;
  color: #003d82; background: rgba(0,61,130,0.08);
  border: 1px solid rgba(0,61,130,0.3); border-radius: 4px;
  padding: 4px 8px; letter-spacing: 0.1em; text-decoration: none; flex-shrink: 0;
}
/* marimo's own theme right-aligns .markdown table cells by default; every
   notebook's vocabulary/grammar/phrase tables need left alignment instead. */
.markdown table td, .markdown table th {
  text-align: left !important;
}
</style>"""

_BADGE = '<a class="tb-badge" href="https://telegram.me/+VuocC5la3ZwyNDky" target="_blank">EEE Community</a>'

_FOOTER_CSS = """
<style>
#eee-footer {
  height: 40px; background: #f5f5f5; border-top: 1px solid #e0e0e0;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  margin: 16px -16px -16px -16px;
  font-family: "DM Mono", monospace;
}
#eee-footer .footer-label { font-size: 10px; color: #1a1a1a; }
#eee-footer a { font-size: 11px; color: #003d82; text-decoration: none; }
</style>"""

_FOOTER_LABEL = {"ru": "Исходный код:", "en": "Source:", "el": "Πηγαίος κώδικας:"}

_QUIZ_FORM_LBL = {"ru": "Форма в тексте:", "en": "Form in text:", "el": "Μορφή στο κείμενο:"}
_QUIZ_DONE     = {
    "ru": "🎉 Все слова пройдены! Нажмите «{btn}» для повтора.",
    "en": "🎉 All words done! Press «{btn}» to repeat.",
    "el": "🎉 Όλες οι λέξεις! Πατήστε «{btn}» για επανάληψη.",
}
_QUIZ_CORR  = {"ru": "Верно:", "en": "Correct:", "el": "Σωστά:"}
_QUIZ_PROGRESS_CORR = {"ru": "правильно", "en": "correct", "el": "σωστά"}
_QUIZ_POS   = {
    "ru": {"noun": "сущ.", "verb": "глаг.", "adj": "прил.", "adv": "нар."},
    "en": {"noun": "n.",   "verb": "v.",    "adj": "adj.",  "adv": "adv."},
    "el": {"noun": "ουσ.", "verb": "ρ.",    "adj": "επίθ.", "adv": "επίρρ."},
}
_QUIZ_RIGHT = {"ru": "✓ Верно!", "en": "✓ Correct!", "el": "✓ Σωστό!"}
_QUIZ_WRONG = {"ru": "✗ Нет. Правильно:", "en": "✗ No. Correct form:", "el": "✗ Όχι. Σωστή μορφή:"}
_WRITE_PLACEHOLDER = {"ru": "греческое слово…", "en": "Greek word…", "el": "ελληνική λέξη…"}
_NAV_NEXT  = {"ru": "Следующий", "en": "Next", "el": "Επόμενο"}
_NAV_AGAIN = {"ru": "Пройти снова", "en": "Again", "el": "Ξανά"}
_NAV_PREV  = {"ru": "Предыдущий", "en": "Prev", "el": "Προηγούμενο"}
_CHECK_LABEL = {"ru": "Проверить", "en": "Check", "el": "Έλεγχος"}
_PARADIGM_NEXT = {"ru": "Следующее", "en": "Next ▸", "el": "Επόμενο"}
_PARADIGM_PREV = {"ru": "Предыдущее", "en": "◂ Prev", "el": "Προηγούμενο"}
_PARADIGM_RESTART = {"ru": "Начать заново", "en": "↺ Start over", "el": "Από την αρχή"}

_STANZA_MATCH_LBL = {
    "ru": {
        "grc_to_tr": "Выберите перевод, соответствующий этой строфе:",
        "tr_to_grc": "Выберите строфу на греческом, соответствующую этому переводу:",
    },
    "en": {
        "grc_to_tr": "Choose the translation matching this stanza:",
        "tr_to_grc": "Choose the Greek stanza matching this translation:",
    },
    "el": {
        "grc_to_tr": "Επιλέξτε τη μετάφραση που ταιριάζει σε αυτή τη στροφή:",
        "tr_to_grc": "Επιλέξτε την ελληνική στροφή που ταιριάζει σε αυτή τη μετάφραση:",
    },
}

_YES_NO = {"ru": ("да", "нет"), "en": ("yes", "no"), "el": ("ναι", "όχι")}

# Worded "incorrect" rather than _QUIZ_WRONG's "Нет"/"No"/"Όχι" -- needed
# wherever a quiz's own answer options could themselves be да/нет (reusing
# _QUIZ_WRONG there would read as restating the answer rather than judging
# it); used elsewhere too since it reads better in general.
_QUIZ_INCORRECT = {
    "ru": "✗ Неверно. Правильно:",
    "en": "✗ Incorrect. Correct answer:",
    "el": "✗ Λάθος. Σωστή απάντηση:",
}

_PRESENCE_LBL = {
    "ru": "Отражено ли это слово в переводе?",
    "en": "Is the word reflected in this translation?",
    "el": "Αποτυπώνεται η λέξη σε αυτή τη μετάφραση;",
}

_PRESENCE_EMPTY = {
    "ru": "Пока нет проверенных пар «слово × перевод» — заполните столбец `reflected` "
          "(yes/no) в translation_presence.tsv.",
    "en": "No reviewed word × translation pairs yet — fill in the `reflected` "
          "(yes/no) column in translation_presence.tsv.",
    "el": "Δεν υπάρχουν ακόμη ελεγμένα ζεύγη λέξη × μετάφραση — συμπληρώστε τη στήλη "
          "`reflected` (yes/no) στο translation_presence.tsv.",
}

_PRESENCE_SOURCE_LBL = {"ru": "оригинал", "en": "original", "el": "πρωτότυπο"}

_PRESENCE_SWITCH_LBL = {
    "ru": "Показать оригинал вместо перевода",
    "en": "Show the original instead of the translation",
    "el": "Εμφάνιση πρωτοτύπου αντί της μετάφρασης",
}


def load_ga_config(path=None) -> "dict | None":
    """Load GA config from a ``ga.json`` file that lives outside the repository.

    Args:
        path: Pass ``__file__`` from a notebook cell to look for ``ga.json``
              next to the notebook. Pass a directory path or an explicit
              ``ga.json`` path for other layouts. Pass ``None`` (default) to
              search in the current working directory.

    Returns a dict such as ``{"measurement_id": "G-XXXXXXXXXX"}``, or
    ``None`` if the file is not found — GA is silently disabled.

    Example cell::

        _ga = load_ga_config(__file__)
        eee_topbar(mo, back_url="...", lang=lang, titles=TITLES, ga_config=_ga)

    The ``ga.json`` file must **not** be committed to the repository — add it
    to ``.gitignore``.  Minimal content::

        {"measurement_id": "G-XXXXXXXXXX"}
    """
    import json as _json
    from pathlib import Path as _Path

    if path is None:
        p = _Path.cwd() / "ga.json"
    else:
        p = _Path(path)
        if p.suffix in (".py", ".ipynb") or (p.is_file() and p.suffix != ".json"):
            p = p.parent / "ga.json"
        elif p.is_dir():
            p = p / "ga.json"

    try:
        return _json.loads(p.read_text()) if p.exists() else None
    except Exception:
        return None


def _find_local(directory, filename) -> "Any | None":
    """Return the path to ``filename`` inside ``directory`` if it exists there, else ``None``.

    The shared "does this exact candidate exist locally" check behind both
    :meth:`ConfigStore.from_file` (which tries two candidate directories)
    and :meth:`GreekUtils._resolve_tsv_path` (which tries one, on behalf of
    both :meth:`GreekUtils.load_vocab_tsv` and
    :meth:`GreekUtils.load_inflected_vocab_tsv`) before either falls back
    to a remote fetch.
    """
    from pathlib import Path as _Path

    p = _Path(directory) / filename
    return p if p.exists() else None


def _raw_base_from_url(url: str) -> str:
    """Return the parent "directory" URL for a raw-content file URL."""
    return url.rsplit("/", 1)[0]


class ConfigStore:
    """Navigation and GA config storage with pluggable backends.

    Use :meth:`from_url`, :meth:`from_file`, :meth:`from_file_or_url`, or
    :meth:`from_dict` to create an instance, then call :meth:`lessons`,
    :meth:`index_url`, and :meth:`ga_config` wherever a notebook needs
    config — the API is identical regardless of storage backend.

    TSV columns: ``url, icon, greek, label, title, desc, index_url`` —
    or per-language variants (``label_ru``, ``title_el``, ...); every
    column present in the file is kept, not just this set. ``url`` and
    ``index_url`` are both complete, ready-to-link URLs — the TSV owns
    hosting-specific details, not the notebook code.

    Example — molab (fetch TSV and GA config from Codeberg)::

        _ROOT = "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main"
        _cfg = ConfigStore.from_url(
            f"{_ROOT}/palaestra/lessons.tsv",
            ga=f"{_ROOT}/ga.json",
        )
        eee_topbar(mo, back_url=_cfg.index_url(), ...)

    Example — local dev (files next to the notebook)::

        _cfg = ConfigStore.from_file(__file__)  # reads lessons.tsv + ga.json

    Example — index/card-list notebooks (local-first, molab-safe)::

        _ROOT = "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main"
        _cfg = ConfigStore.from_file_or_url(
            __file__, f"{_ROOT}/palaestra/lessons.tsv", ga=f"{_ROOT}/ga.json",
        )
    """

    def __init__(self, lessons: "list[dict]", ga: "dict | None" = None, *,
                 _raw_base: "str | None" = None):
        self._lessons = lessons
        self._ga = ga or {}
        self._raw_base = _raw_base

    @classmethod
    def _parse_tsv(cls, text: str) -> "list[dict]":
        """Parse a lessons TSV, keeping every column the file actually has.

        Not restricted to the common single-language schema (``url``,
        ``icon``, ``greek``, ``label``, ``title``, ``desc``, ``index_url``)
        — courses with per-language columns (``label_ru``, ``title_el``,
        ...) get those back too.
        """
        import csv as _csv
        import io as _io
        return list(_csv.DictReader(_io.StringIO(text), delimiter="\t"))

    # ── Factory methods ───────────────────────────────────────────────────────

    @classmethod
    def from_file(cls, path=None) -> "ConfigStore":
        """Load from ``lessons.tsv`` + ``ga.json`` next to ``path``.

        Pass ``__file__`` from a notebook cell. Walks up one level if the
        files are not found in the same directory (lesson-in-subdir layout).
        Missing files are silently ignored.
        """
        from pathlib import Path as _Path

        base = (_Path(path).parent if path and _Path(path).is_file() else
                _Path(path) if path else _Path.cwd())

        tsv = _find_local(base, "lessons.tsv") or _find_local(base.parent, "lessons.tsv")
        lessons = cls._parse_tsv(tsv.read_text(encoding="utf-8")) if tsv else []
        return cls(lessons, load_ga_config(path) or {})

    @classmethod
    def from_url(
        cls, url: str, ga: "dict | str | None" = None, timeout: int = 5
    ) -> "ConfigStore":
        """Fetch a lessons TSV from ``url`` and build a ConfigStore.

        ``ga`` can be:

        - a dict ``{"measurement_id": "G-..."}`` — used as-is
        - a URL string — fetched and parsed as JSON
        - ``None`` — no GA config

        On network failure the ConfigStore is empty (no lessons, no GA) but
        ``nb_remote()`` still works because ``_raw_base`` is derived from the
        URL without a network call.
        """
        import json as _json
        import urllib.request as _req

        _raw_base = _raw_base_from_url(url)
        try:
            with _req.urlopen(url, timeout=timeout) as _f:
                lessons = cls._parse_tsv(_f.read().decode("utf-8"))
            if isinstance(ga, str):
                with _req.urlopen(ga, timeout=timeout) as _f:
                    ga = _json.loads(_f.read().decode("utf-8"))
        except Exception:
            lessons = []
            ga = {}
        return cls(lessons, ga or {}, _raw_base=_raw_base)

    @classmethod
    def from_dict(cls, lessons: "list[dict]", ga: "dict | None" = None) -> "ConfigStore":
        """Create from in-memory data — embed config inline in a notebook."""
        return cls(list(lessons), ga or {})

    @classmethod
    def from_file_or_url(
        cls, path, url: str, ga: "dict | str | None" = None, timeout: int = 5
    ) -> "ConfigStore":
        """Load ``lessons.tsv`` from next to ``path`` if present; else fetch ``url``.

        Local-dev-friendly: a real local checkout (or a course being edited
        before its first push) reads its own ``lessons.tsv`` straight off
        disk, walking up one level like :meth:`from_file` — no network call,
        no molab-only 404. Once the file genuinely isn't there (e.g. running
        from a fresh molab upload), falls back to :meth:`from_url`.

        ``raw_base`` is always derived from ``url``, even when lessons load
        from disk, so ``nb_remote()``/``raw_base`` still work for fetching
        other remote assets (images, PDFs) regardless of where the lesson
        list itself came from. GA config is only read locally (next to
        ``path``) in the local-file branch — not fetched remotely just
        because lessons loaded from disk.
        """
        local = cls.from_file(path)
        if local.lessons():
            local._raw_base = _raw_base_from_url(url)
            return local
        return cls.from_url(url, ga=ga, timeout=timeout)

    # ── Accessors ─────────────────────────────────────────────────────────────

    def lessons(self) -> "list[dict]":
        """Return all lesson rows as a list of dicts."""
        return list(self._lessons)

    def ga_config(self) -> "dict | None":
        """Return GA config dict (``{"measurement_id": "G-..."}``), or ``None``."""
        return dict(self._ga) if self._ga else None

    def index_url(self) -> "str | None":
        """Return the back-link URL from the first lesson row's ``index_url`` column."""
        return self._lessons[0].get("index_url") if self._lessons else None

    @property
    def raw_base(self) -> "str | None":
        """Raw Codeberg base URL (parent of the lessons.tsv directory), or None."""
        return self._raw_base

    def nb_remote(self, nb_file_or_name: str) -> str:
        """Return the raw Codeberg base URL for the calling notebook's directory.

        Only available when the instance was created via :meth:`from_url`.
        Preferred usage — pass the lesson directory name explicitly::

            NB_REMOTE = cfg.nb_remote("2026_06_16")

        Legacy usage (fragile in containers where ``__file__`` may be wrong)::

            NB_REMOTE = cfg.nb_remote(__file__)
        """
        if self._raw_base is None:
            raise RuntimeError("nb_remote() requires ConfigStore.from_url — no remote base known")
        from pathlib import Path
        p = Path(nb_file_or_name)
        # Plain name "2026_06_16" → use as-is; file path "/foo/2026_06_16/nb.py" → use parent name
        dir_name = p.parent.name if p.parent != Path(".") else p.name
        return f"{self._raw_base}/{dir_name}"


def eee_topbar(mo, back_url: str, lang: str, titles: "dict | str", *, style: str = "back", icon: str = "●", ga_config=None, parent_titles: "dict | str | None" = None):
    """Render the EEE sticky navigation topbar.

    Must be the **last expression** in a marimo cell — no trailing ``return``.

    Args:
        mo:            The marimo module (passed from the cell's imports).
        back_url:      URL for the left-side link. Pass ``None`` or ``""`` to
                       suppress the link — in ``style="back"`` this hides the
                       whole bar (except GA); in ``style="index"`` the icon
                       and title still render, just as plain (non-link) text.
        lang:          Current language code (e.g. ``"ru"``, ``"el"``, ``"en"``).
        titles:        This page's own name, as a ``{lang: name}`` dict or a
                       plain string. In ``style="index"`` with no
                       ``back_url``, shown as a plain-text self-badge.
        style:         ``"back"`` (default) renders "◀ {title}" linking to
                       ``back_url`` — for content pages one level below an
                       index. ``"index"`` is for index/landing pages: with no
                       ``back_url`` it renders "{icon} {title}" as plain
                       text (a top-level index, or one scoped only to its own
                       level); with a ``back_url`` (an index that points up
                       to a parent index) it renders "◀ {parent_titles}" as
                       a link — the *parent's* name, not this page's own, so
                       pass ``parent_titles`` too or the link mislabels
                       itself with the wrong page's name.
        icon:          Glyph shown before the title in ``style="index"``
                       when there's no ``back_url`` (self-badge case only).
        ga_config:     Dict from :func:`load_ga_config`, or ``None`` to skip GA.
        parent_titles: Name of the index ``back_url`` points to, as a
                       ``{lang: name}`` dict or plain string. Only used in
                       ``style="index"`` when ``back_url`` is set. Falls back
                       to ``titles`` (this page's own name) if not given —
                       kept working for existing callers, but that mislabels
                       the link, so always pass it once ``back_url`` comes
                       from :func:`parent_back_url`.

    Example cell::

        from eee_project.notebook_utils import eee_topbar, load_ga_config
        _ga = load_ga_config(__file__)
        _TITLES = {"ru": "Каподистриас", "el": "Καποδίστριας", "en": "Kapodistrias"}
        eee_topbar(mo, back_url="https://molab.marimo.io/...", lang=lang_sel.value,
                   titles=_TITLES, ga_config=_ga)

        # index/landing page, linking up to a parent index:
        eee_topbar(mo, back_url="https://.../created_with_eee/", lang=lang_sel.value,
                   titles="Kapodistrias", parent_titles="created_with_eee", style="index")
    """
    ga_widget = _make_ga_widget(mo, ga_config)
    title = titles.get(lang, next(iter(titles.values()))) if isinstance(titles, dict) else titles
    if style == "index":
        if back_url:
            _parent = parent_titles if parent_titles is not None else titles
            parent_title = _parent.get(lang, next(iter(_parent.values()))) if isinstance(_parent, dict) else _parent
            left = f'<a class="tb-back" href="{back_url}" target="_blank" rel="noopener">◀ {parent_title}</a>'
        else:
            left = f'<span class="tb-back">{icon} {title}</span>'
    elif not back_url:
        return ga_widget
    else:
        left = f'<a class="tb-back" href="{back_url}" target="_blank" rel="noopener">◀ {title}</a>'
    bar = mo.Html(f"""{_TOPBAR_CSS}
<div id="eee-topbar">
  {left}
  {_BADGE}
</div>""")
    return mo.vstack([bar, ga_widget], gap=0) if ga_widget is not None else bar


@functools.lru_cache(maxsize=32)
def parent_back_url(parent_url: str, *, timeout: int = 5) -> "str | None":
    """Resolve ``eee_topbar``'s ``back_url`` for a course/grouping-index page.

    Fetches the *parent* index's own ``lessons.tsv`` over the network and
    returns its ``index_url``. Every row in a grouping-level ``lessons.tsv``
    should carry the same value: the parent page's own URL, repeated per row
    exactly like lesson-level ``index_url`` already is one level down.

    Deliberately remote-only, no local-first check: molab only bundles the
    calling notebook's own directory, never a parent's — a
    ``Path(__file__).parent.parent`` local lookup here would silently find
    nothing on molab every time (see this project's own CLAUDE.md gotcha:
    "never read a file from a parent directory with a bare
    ``Path(__file__).parent.parent / 'x'``" — correct in every local test,
    silently broken on the real hosted deployment). An earlier version of
    this function tried the local-first shortcut anyway and shipped broken.

    Cached per ``(parent_url, timeout)`` for the life of the kernel —
    calling this from a cell that also depends on unrelated reactive state
    (e.g. a language selector) won't repeat the network fetch on every
    re-render, even if the caller doesn't isolate it into its own cell.

    Args:
        parent_url: Remote URL of the parent's ``lessons.tsv``.
        timeout:    Network timeout in seconds.

    Example cell (course index one level below a grouping index)::

        from eee_project.notebook_utils import parent_back_url
        back_url = parent_back_url(
            f"{_ROOT}/modern_greek/b1greeklanguageandculture/lessons.tsv",
        )
        eee_topbar(mo, back_url=back_url, lang=lang, titles=TITLES, style="index")
    """
    return ConfigStore.from_url(parent_url, timeout=timeout).index_url()


_HERO_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;700;800&display=swap');
.eee-hero { text-align: center; padding: 32px 16px 24px; font-family: Syne, sans-serif; }
.eee-series {
  font-family: "DM Mono", monospace; font-size: 11px; color: #003d82;
  letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 10px;
}
.eee-title {
  font-size: 26px; font-weight: 800; letter-spacing: -0.02em;
  background: linear-gradient(90deg, #003d82, #5f27cd);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 6px;
}
.eee-subtitle { font-size: 14px; color: #666; }
</style>
"""


def eee_hero(mo, lang: str, titles: "dict[str, tuple[str, str]]", *, lang_fallback: str = "el"):
    """Render the EEE index-page hero title block.

    Must be the **last expression** in a marimo cell — no trailing ``return``.

    Args:
        mo:            The marimo module.
        lang:          Current language code (e.g. ``"ru"``, ``"el"``, ``"en"``).
        titles:        ``{lang: (title, subtitle)}`` — falls back to
                       ``lang_fallback`` when ``lang`` has no entry.
        lang_fallback: Language to fall back to. Default ``"el"``.

    Example cell::

        from eee_project.notebook_utils import eee_hero
        eee_hero(mo, lang_sel.value, {
            "ru": ("Каподистриас", "Серия уроков"),
            "el": ("Καποδίστριας", "Σειρά μαθημάτων"),
            "en": ("Kapodistrias", "Lesson series"),
        })
    """
    title, subtitle = titles.get(lang, titles[lang_fallback])
    return mo.Html(f"""{_HERO_CSS}
<div class="eee-hero">
  <div class="eee-title">{title}</div>
  <div class="eee-series">{subtitle}</div>
</div>""")


_CARD_LIST_CSS = """
<style>
.eee-card, .eee-card-disabled {
  display: block; text-decoration: none; color: #1a1a1a;
  background: #f8f9fa; border: 1px solid #e0e0e0;
  border-radius: 12px; padding: 20px; margin-bottom: 14px;
  font-family: Syne, sans-serif;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.eee-card:hover { border-color: rgba(0,61,130,.25); box-shadow: 0 0 18px rgba(0,61,130,.07); }
.eee-card-disabled { opacity: 0.55; }
.eee-card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.eee-card-icon {
  font-size: 26px; width: 46px; height: 46px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0,61,130,.06); border-radius: 10px;
}
.eee-card-label {
  font-family: "DM Mono", monospace; font-size: 10px; color: #003d82;
  letter-spacing: .12em; text-transform: uppercase; margin-bottom: 2px;
}
.eee-card-title { font-size: 16px; font-weight: 700; }
.eee-card-greek { font-family: "DM Mono", monospace; font-size: 12px; color: #5f27cd; margin-top: 1px; }
.eee-card-desc { font-size: 13px; color: #666; line-height: 1.5; }
.eee-card-arrow {
  text-align: right; margin-top: 10px;
  font-family: "DM Mono", monospace; font-size: 11px; color: #5f27cd;
}
</style>
"""

_CARD_LIST_SOON = {"ru": "скоро", "el": "σύντομα", "en": "coming soon"}


def eee_card_list(mo, cfg: "ConfigStore", lang: str, *, lang_fallback: str = "el"):
    """Render the EEE index-page lesson/course card list.

    Must be the **last expression** in a marimo cell — no trailing ``return``.

    Reads rows from ``cfg.lessons()``. Each row needs ``url``, ``icon``,
    ``greek``, and ``label_<lang>``/``title_<lang>``/``desc_<lang>`` columns
    — text falls back to ``lang_fallback`` when the current ``lang`` has no
    translation. ``url`` is used verbatim (no molab-specific construction —
    the TSV owns the full URL, so notebooks stay portable to other hosting).
    A falsy ``url`` renders a disabled "coming soon" card. Card links use
    ``target="_blank" rel="noopener"``. Renders a translated "couldn't load"
    message instead when ``cfg.lessons()`` comes back empty.

    Args:
        mo:            The marimo module.
        cfg:           A loaded ``ConfigStore`` (from the topbar's setup cell).
        lang:          Current language code (e.g. ``"ru"``, ``"el"``, ``"en"``).
        lang_fallback: Language suffix for row text and the "soon"/error
                       strings when ``lang`` isn't translated. Default ``"el"``.

    Example cell::

        from eee_project.notebook_utils import eee_card_list
        eee_card_list(mo, cfg, lang_sel.value)
    """
    rows = cfg.lessons()
    if not rows:
        _tsv_url = f"{cfg.raw_base}/lessons.tsv"
        _load_error = {
            "ru": f"Не удалось загрузить файл: {_tsv_url}\n\nПроверьте, что он доступен по этой ссылке.",
            "el": f"Δεν ήταν δυνατή η φόρτωση του αρχείου: {_tsv_url}\n\nΕλέγξτε αν είναι προσβάσιμο σε αυτόν τον σύνδεσμο.",
            "en": f"Couldn't load file: {_tsv_url}\n\nCheck that it's accessible at that link.",
        }
        return mo.md(_load_error.get(lang, _load_error[lang_fallback]))

    soon = _CARD_LIST_SOON.get(lang, _CARD_LIST_SOON[lang_fallback])
    label_key, label_fb = f'label_{lang}', f'label_{lang_fallback}'
    title_key, title_fb = f'title_{lang}', f'title_{lang_fallback}'
    desc_key, desc_fb = f'desc_{lang}', f'desc_{lang_fallback}'
    cards = []
    for row in rows:
        url = row["url"] or None
        inner = f"""<div class="eee-card-header">
              <div class="eee-card-icon">{row['icon']}</div>
              <div>
                <div class="eee-card-label">{row.get(label_key, row[label_fb])}</div>
                <div class="eee-card-title">{row.get(title_key, row[title_fb])}</div>
                <div class="eee-card-greek">{row['greek']}</div>
              </div>
            </div>
            <div class="eee-card-desc">{row.get(desc_key, row[desc_fb])}</div>"""
        if url:
            cards.append(f'<a class="eee-card" href="{url}" target="_blank" rel="noopener">{inner}<div class="eee-card-arrow">◀</div></a>')
        else:
            cards.append(f'<div class="eee-card eee-card-disabled">{inner}<div class="eee-card-arrow">{soon}</div></div>')

    return mo.Html(_CARD_LIST_CSS + "\n".join(cards))


def eee_footer(mo, lang: str):
    """Render the EEE source footer bar.

    Must be the **last expression** in a marimo cell — no trailing ``return``.

    Args:
        mo:   The marimo module.
        lang: Current language code for the "Source:" label.

    Example cell::

        from eee_project.notebook_utils import eee_footer
        eee_footer(mo, lang=lang_sel.value)
    """
    lbl = _FOOTER_LABEL.get(lang, _FOOTER_LABEL["en"])
    return mo.Html(f"""{_FOOTER_CSS}
<div id="eee-footer">
  <span class="footer-label">{lbl}</span>
  <a href="https://codeberg.org/EEE-project" target="_blank">codeberg.org/EEE-project</a>
</div>""")


def magnify_image(mo, path, *, raw_base: str, width: "int | None" = None,
                   prefer_local: bool = False) -> Any:
    """Render an image that opens full-size in a new tab on click.

    The click-through ``<a href>`` always points at a remote raw-content URL
    (``raw_base`` + the file's name), never a base64 data-URI — confirmed in
    practice that a data-URI does NOT reliably open on click when the page is
    embedded in a sandboxed iframe (molab and the TG mini-app wrappers both
    embed notebooks this way). That constraint is about the click *target*,
    not image *display*: by default the inline thumbnail ``<img src>`` also
    uses that same remote URL (so it benefits from normal HTTP caching), but
    pass ``prefer_local=True`` to instead read the local file directly (as a
    data-URI) when present, falling back to the remote URL only if it isn't.
    That's for a lesson whose images haven't been pushed yet: the thumbnail
    renders immediately in local dev/preview rather than 404ing until the
    first push. Leave the default off for already-published lessons — it
    only trades away caching for a problem they don't have. Do not point the
    ``<a href>`` at a data-URI either way — that reintroduces the
    click-through bug this function exists to avoid.

    Args:
        mo:           The marimo module.
        path:         ``pathlib.Path`` to the local copy of the image.
        raw_base:     Base raw-content URL for the file's directory, e.g.
                       ``"https://codeberg.org/ORG/REPO/raw/branch/main/dir"``.
                       Required (no default) so every call site names its own
                       repo/branch/path explicitly.
        width:        Optional max-width in pixels for the inline thumbnail.
        prefer_local: When ``True``, read the thumbnail from the local file
                       (data-URI) if it exists, instead of the remote URL.
                       Default ``False`` matches every existing call site.

    Example cell::

        from pathlib import Path
        from eee_project.notebook_utils import magnify_image
        magnify_image(
            mo, Path(__file__).parent / "map.jpg",
            raw_base="https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/odyssey/2026_06_15",
            width=280,
        )
    """
    url = f"{raw_base.rstrip('/')}/{path.name}"
    if prefer_local and path.exists():
        import base64
        import mimetypes
        _mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        _b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        img_src = f"data:{_mime};base64,{_b64}"
    else:
        img_src = url
    style = f"max-width:{width}px;" if width else "max-width:100%;"
    return mo.Html(
        f'<a href="{url}" target="_blank" rel="noopener">'
        f'<img src="{img_src}" style="{style}width:100%;border-radius:4px;'
        f'object-fit:cover;cursor:pointer"/>'
        f'</a>'
    )


# ════════════════════════════════════════ polytonic diacritics bar ══

try:
    import anywidget as _anywidget
    import traitlets as _traitlets
    _ANYWIDGET_OK = True
except ImportError:
    _ANYWIDGET_OK = False


# ═══════════════════════════════════ GA4 pageview tracker (anywidget) ══
# mo.Html() can't execute inline <script> tags — content inserted that way
# is inert, the same browser rule that makes innerHTML-inserted scripts
# inert (present in the DOM, never run). This is true on any marimo-
# rendered page, molab or local, not a molab-specific limitation. A real
# anywidget render() call, by contrast, genuinely executes: it fires
# gtag's tracking calls directly and dynamically creates the external
# <script src="...gtag/js"> tag via createElement+appendChild, which does
# execute (only *inline*, innerHTML-inserted scripts are inert — a
# dynamically created element is not).

_GA_ESM_TMPL = """\
function render({ el }) {
  el.style.display = "none";
  const id = EEE_MEASUREMENT_ID;

  const s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + id;
  document.head.appendChild(s);

  window.dataLayer = window.dataLayer || [];
  function gtag(){ window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag("js", new Date());
  gtag("config", id);
}
export default { render };
"""


def _make_ga_esm(measurement_id: str) -> str:
    import json as _json
    return _GA_ESM_TMPL.replace("EEE_MEASUREMENT_ID", _json.dumps(measurement_id))


@functools.lru_cache(maxsize=8)
def _make_ga_widget_class(measurement_id: str):
    return type("_GaTag", (_anywidget.AnyWidget,), {
        "_esm": _make_ga_esm(measurement_id),
    })


def _make_ga_widget(mo, ga_config: "dict | None"):
    """Return an anywidget instance that fires a GA4 pageview, or None if
    ga_config has no measurement_id or anywidget isn't installed — either
    way GA is silently skipped."""
    measurement_id = ga_config.get("measurement_id") if ga_config else None
    if not measurement_id or not _ANYWIDGET_OK:
        return None
    return mo.ui.anywidget(_make_ga_widget_class(measurement_id)())


_BAR_CSS_TMPL = """\
EEE_BAR{display:flex;flex-wrap:wrap;gap:5px;EEE_MARGIN;align-items:center}
EEE_BAR .dia-lbl{font-size:12px;color:#555;margin-right:4px;font-family:sans-serif}
EEE_BAR button{min-width:52px;min-height:50px;padding:2px 8px;border:1px solid #bbb;
  border-radius:8px;background:#fafafa;cursor:pointer;line-height:1.1;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  touch-action:manipulation;-webkit-tap-highlight-color:transparent;
  font-family:'GFS Didot','New Athena Unicode','Noto Serif',serif}
EEE_BAR button:active{background:#e8f4ff;border-color:#003d82}
EEE_BAR button.dia-active{background:#dceeff;border-color:#003d82;box-shadow:inset 0 2px 4px rgba(0,61,130,0.2)}
EEE_BAR .dia-ch{font-size:26px}
EEE_BAR .dia-sub{font-size:9px;color:#555;font-family:sans-serif;margin-top:1px}
EEE_BAR .dia-clr{background:#fff5f5;border-color:#ffcdd2;font-family:sans-serif}
EEE_BAR .dia-clr .dia-ch{font-size:18px}
EEE_BAR .dia-clr:active{background:#ffcdd2}
"""


def _bar_css(selector: str, margin: str = "margin:6px 0 4px") -> str:
    return _BAR_CSS_TMPL.replace("EEE_BAR", selector).replace("EEE_MARGIN", margin)


_DIA_CSS = _bar_css(".eee-dia-bar") + """\
.eee-dia-inp{width:100%;box-sizing:border-box;padding:6px 8px;font-size:16px;
  border:1px solid #ccc;border-radius:4px;margin-top:2px;
  font-family:'GFS Didot','New Athena Unicode','Noto Serif',serif}
"""

# Shared by both diacritics-bar ESM widgets (_DIA_ESM_TMPL, _PARA_ESM) --
# was duplicated verbatim in each until 2026-07-26. clearMarks/clearAllMarks/
# getMarksFor take `activeMarks` as an explicit parameter rather than closing
# over it, since each widget's render() owns its own per-instance Map and
# these functions now live at module level, shared across every instance.
_DIACRITIC_CORE_JS = """\
const ALL_MARKS = [
  {ch: 'ά', dia: '\\u0301', label: 'acute',  cat: 'accent'},
  {ch: 'ὰ', dia: '\\u0300', label: 'grave',  cat: 'accent'},
  {ch: 'ᾶ', dia: '\\u0342', label: 'tilde',  cat: 'accent'},
  {ch: 'ἁ', dia: '\\u0314', label: 'rough',  cat: 'breath'},
  {ch: 'ἀ', dia: '\\u0313', label: 'smooth', cat: 'breath'},
  {ch: 'ᾳ', dia: '\\u0345', label: 'iotsub', cat: 'subscr'},
  {ch: 'ϊ', dia: '\\u0308', label: 'diaer',  cat: 'diaer'},
];

// Clicking a mark clears its own category plus any listed exclusions.
const EXCL = {
  accent: ['accent'],
  breath: ['breath', 'diaer'],
  subscr: ['subscr', 'diaer'],
  diaer:  ['diaer', 'breath', 'subscr'],
};

// Canonical order: breathing must precede accent in NFD for correct NFC composition.
// (Both have CCC 230, so Unicode does not reorder them automatically.)
const CAT_ORDER = {breath: 0, accent: 1, diaer: 2, subscr: 3};

const VOWELS = new Set('αεηιουωΑΕΗΙΟΥΩ');
const DIA_VOWELS = {
  '\\u0342': new Set('αηιυωΑΗΙΥΩ'),
  '\\u0345': new Set('αηωΑΗΩ'),
  '\\u0308': new Set('ιυΙΥ'),
};

function getMarksFor(activeMarks, base) {
  const m = [...activeMarks.entries()]
    .sort(([a], [b]) => (CAT_ORDER[a] ?? 9) - (CAT_ORDER[b] ?? 9))
    .filter(([, {dia}]) => { const s = DIA_VOWELS[dia]; return !s || s.has(base); })
    .map(([, {dia}]) => dia).join('');
  return m || null;
}

function clearMarks(activeMarks, ...cats) {
  for (const cat of cats) {
    const m = activeMarks.get(cat);
    if (m) { m.btn.classList.remove('dia-active'); activeMarks.delete(cat); }
  }
}

function clearAllMarks(activeMarks) {
  for (const {btn} of activeMarks.values()) btn.classList.remove('dia-active');
  activeMarks.clear();
}

function makeMarkButton(ch, label) {
  const btn = document.createElement('button');
  btn.innerHTML = `<span class="dia-ch">${ch}</span><span class="dia-sub">${label}</span>`;
  btn.addEventListener('mousedown', e => e.preventDefault());
  return btn;
}

function makeClearButton() {
  const btn = document.createElement('button');
  btn.className = 'dia-clr';
  btn.innerHTML = '<span class="dia-ch">✕</span><span class="dia-sub">clear</span>';
  btn.addEventListener('mousedown', e => e.preventDefault());
  return btn;
}

// Toggles `cat`'s mark: clears it if `dia` is already the active mark for
// that category, otherwise clears whatever EXCL[cat] conflicts with it and
// activates this one. Pure activeMarks/DOM-class mutation -- doesn't touch
// focus, since which element to refocus differs by widget (a single fixed
// input vs. whichever field currently has focus).
function toggleMark(activeMarks, cat, dia, btn) {
  const cur = activeMarks.get(cat);
  if (cur && cur.dia === dia) {
    clearMarks(activeMarks, cat);
  } else {
    clearMarks(activeMarks, ...(EXCL[cat] || [cat]));
    activeMarks.set(cat, {dia, btn});
    btn.classList.add('dia-active');
  }
}

// Strips the diacritic marks from the character immediately before `pos` in
// `inp.value` (NFD-decompose, drop combining marks, NFC-recompose) and
// updates inp.value + its selection to match. Returns the new cursor
// position, or null if pos was 0 (nothing before the cursor to strip --
// caller decides what "nothing to do" means for it, e.g. still refocusing).
// Deliberately does not persist the change (model.set/save_changes) or
// refocus -- callers persist differently (immediate vs. debounced).
function stripLastDiacritic(inp, pos) {
  if (pos === 0) return null;
  const chars = Array.from(inp.value.slice(0, pos));
  const last = chars.pop();
  const stripped = last.normalize('NFD').replace(/[̀-ͯ]/g, '').normalize('NFC');
  const pre = chars.join('');
  inp.value = pre + stripped + inp.value.slice(pos);
  const newPos = pre.length + stripped.length;
  inp.setSelectionRange(newPos, newPos);
  return newPos;
}
"""

# The input lives INSIDE the widget so beforeinput fires without crossing
# the marimo-text shadow DOM boundary.
# EEE_PLACEHOLDER and EEE_LABEL are replaced at runtime by _make_dia_esm().
# Only `value` is synced so mo.ui.anywidget().value returns a plain string.
_DIA_ESM_TMPL = _DIACRITIC_CORE_JS + """\
function render({ model, el }) {
  const activeMarks = new Map(); // cat → {dia, btn}
  let biSnapshot = null;         // {value, pos} saved in beforeinput for Android fix

  const bar = document.createElement('div');
  bar.className = 'eee-dia-bar';

  const lbl = EEE_LABEL;
  if (lbl) {
    const sp = document.createElement('span');
    sp.className = 'dia-lbl';
    sp.textContent = lbl;
    bar.appendChild(sp);
  }

  const inp = document.createElement('input');
  inp.type = 'text';
  inp.className = 'eee-dia-inp';
  inp.placeholder = EEE_PLACEHOLDER;

  for (const {ch, dia, label, cat} of ALL_MARKS) {
    const btn = makeMarkButton(ch, label);
    btn.addEventListener('click', () => {
      toggleMark(activeMarks, cat, dia, btn);
      inp.focus();
    });
    bar.appendChild(btn);
  }

  const clr = makeClearButton();
  clr.addEventListener('click', () => {
    clearAllMarks(activeMarks);
    const pos = inp.selectionStart ?? inp.value.length;
    const newPos = stripLastDiacritic(inp, pos);
    if (newPos !== null) {
      model.set('value', inp.value);
      model.save_changes();
      inp.setSelectionRange(newPos, newPos);
    }
    inp.focus();
  });
  bar.appendChild(clr);

  inp.addEventListener('beforeinput', e => {
    biSnapshot = null;
    if (!activeMarks.size || (e.inputType !== 'insertText' && e.inputType !== 'insertCompositionText') || !e.data) return;
    const base = e.data.normalize('NFD')[0];
    if (!VOWELS.has(base)) { clearAllMarks(activeMarks); return; }
    const marks = getMarksFor(activeMarks, base);
    if (!marks) return;
    e.preventDefault();
    const start = inp.selectionStart ?? inp.value.length;
    const end   = inp.selectionEnd   ?? start;
    const composed = (base + marks).normalize('NFC');
    const newVal = inp.value.slice(0, start) + composed + inp.value.slice(end);
    const newPos = start + composed.length;
    inp.value = newVal;
    inp.setSelectionRange(newPos, newPos);
    biSnapshot = {value: newVal, pos: newPos};
    model.set('value', newVal);
    model.save_changes();
  });

  inp.addEventListener('input', e => {
    if (biSnapshot) {
      // Android ignored beforeinput.preventDefault() (inputType may be insertCompositionText).
      // Restore the composed state we saved in beforeinput.
      inp.value = biSnapshot.value;
      inp.setSelectionRange(biSnapshot.pos, biSnapshot.pos);
      biSnapshot = null;
      model.set('value', inp.value);
      model.save_changes();
      return;
    }
    model.set('value', inp.value);
    model.save_changes();
  });

  // keydown handles desktop Enter (stopPropagation prevents marimo eating it;
  // preventDefault prevents form double-submit)
  inp.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      e.stopPropagation();
      model.set('enter_pressed', (model.get('enter_pressed') || 0) + 1);
      model.save_changes();
    }
  });

  // form submit handles mobile "Go" button (doesn't fire keydown 'Enter')
  const form = document.createElement('form');
  form.style.display = 'contents';
  form.addEventListener('submit', e => {
    e.preventDefault();
    model.set('enter_pressed', (model.get('enter_pressed') || 0) + 1);
    model.save_changes();
  });
  form.appendChild(inp);

  inp.value = model.get('value') || '';
  model.on('change:value', () => { inp.value = model.get('value') || ''; });

  el.appendChild(bar);
  el.appendChild(form);
}
export default { render };
"""


def _make_dia_esm(placeholder: str, label: str) -> str:
    import json as _json
    return (_DIA_ESM_TMPL
            .replace("EEE_PLACEHOLDER", _json.dumps(placeholder))
            .replace("EEE_LABEL", _json.dumps(label)))


@functools.lru_cache(maxsize=8)
def _make_dia_widget_class(placeholder: str, label: str):
    return type("_DiacriticsTextWidget", (_anywidget.AnyWidget,), {
        "_css": _DIA_CSS,
        "_esm": _make_dia_esm(placeholder, label),
        "value": _traitlets.Unicode("").tag(sync=True),
        "enter_pressed": _traitlets.Int(0).tag(sync=True),
    })


class _DiacriticsElement:
    """Thin wrapper: exposes .value as a plain string; display forwards to widget."""

    def __init__(self, ui_widget: Any) -> None:
        self._ui = ui_widget

    @property
    def value(self) -> str:
        return self._ui.widget.value

    @property
    def enter_pressed(self) -> int:
        """Increments each time Enter is pressed in the input — treat as a second
        "check requested" signal alongside a submit button's own click counter
        (same convention as ``make_paradigm_form``'s ``.widget.submit_request["request_id"]``)."""
        return self._ui.widget.enter_pressed

    def _mime_(self) -> Any:
        return self._ui._mime_()


def diacritics_text(mo, *, placeholder: str = "", label: str = "", value: str = "") -> Any:
    """Combined polytonic diacritics bar + text input widget.

    Returns an element whose ``.value`` is the typed text as a plain string
    (drop-in for ``mo.ui.text().value``).
    Buttons stay highlighted until pressed again (persistent diacritic mode).
    Requires ``anywidget``. See ``GreekUtils.word_write_question`` for the
    ``.enter_pressed`` reactivity caveat if hand-rolling a cell around this.
    """
    if not _ANYWIDGET_OK:
        return mo.ui.text(placeholder=placeholder or "Greek word…", full_width=True,
                          value=value)
    cls = _make_dia_widget_class(placeholder, label)
    inst = cls()
    if value:
        inst.value = value
    return _DiacriticsElement(mo.ui.anywidget(inst))


# ════════════════════════════════════════ paradigm form widget ══

_PARA_CSS = _bar_css(".eee-para-bar", "margin:6px 0 8px") + """\
.eee-para-row{display:flex;align-items:center;gap:10px;margin:3px 0}
.eee-para-lbl{min-width:58px;font-size:13px;color:#444;font-family:sans-serif;text-align:right}
.eee-para-inp{flex:1;padding:5px 8px;font-size:15px;border:1px solid #ccc;border-radius:4px;
  font-family:'GFS Didot','New Athena Unicode','Noto Serif',serif}
.eee-para-inp:focus{outline:none;border-color:#003d82;box-shadow:0 0 0 2px rgba(0,61,130,0.15)}
"""

_PARA_ESM = _DIACRITIC_CORE_JS + r"""
// Modern Greek monotonic orthography (post-1982) only uses the acute accent
// and diaeresis -- grave/circumflex accent and breathing/iota-subscript are
// polytonic-only and would confuse a Modern Greek exercise, not just clutter it.
const MONOTONIC_MARKS=ALL_MARKS.filter(m=>m.label==='acute'||m.cat==='diaer');

function render({model,el}){
  // anywidget calls this fresh for every new widget instance, and
  // make_paradigm_form() always constructs a brand-new _ParadigmFormWidget
  // (paradigm_drill_widgets() creates one per word, never reuses/caches
  // one across words) -- so the lock state below is naturally scoped to
  // one word's drill. If that ever changes (e.g. a widget instance gets
  // reused/cached across words), the lock-request bookkeeping would need
  // to be reset explicitly on each new word instead.
  const MARKS=model.get('polytonic')?ALL_MARKS:MONOTONIC_MARKS;
  const activeMarks=new Map();
  let focusedInp=null;
  let biSnap=null;
  // submit_request.request_id doubles as the request id (each fireSubmit
  // sends the next value and every reply echoes back the one it answered),
  // so no separate "last sent" counter is needed -- model.get('submit_request')
  // after a model.set() already reads the just-sent value, synchronously,
  // before save_changes() does the real network round trip.
  const pendingOrigin=new Map();  // request_id -> origin field index, while its reply is in flight

  // A field can (rarely) have more than one request in flight -- fireSubmit
  // itself refuses to re-lock an already-locked field, but the mobile "Go"
  // form-submit path and the keydown path both funnel through it, so treat
  // this as belt-and-suspenders rather than assuming it can't happen. Only
  // actually unlock once no *other* pending request still names this field --
  // unlocking on any single reply, even a stale or superseded one, would
  // reopen the corruption window for whichever request is still outstanding.
  function releaseLock(idx){
    for(const v of pendingOrigin.values())if(v===idx)return;
    inputs[idx].readOnly=false;
  }

  let _debTimer;
  function flushValues(){
    model.set('values',inputs.map(inp=>inp.value));
  }
  function updateValues(){
    clearTimeout(_debTimer);
    _debTimer=setTimeout(()=>{flushValues();model.save_changes();},300);
  }

  const bar=document.createElement('div');
  bar.className='eee-para-bar';

  for(const{ch,dia,label,cat}of MARKS){
    const btn=makeMarkButton(ch,label);
    btn.addEventListener('click',()=>{
      toggleMark(activeMarks,cat,dia,btn);
      if(focusedInp)focusedInp.focus();
    });
    bar.appendChild(btn);
  }

  const clrBtn=makeClearButton();
  clrBtn.addEventListener('click',()=>{
    clearAllMarks(activeMarks);
    if(!focusedInp||focusedInp.readOnly)return;
    const inp=focusedInp;
    const pos=inp.selectionStart??inp.value.length;
    const newPos=stripLastDiacritic(inp,pos);
    if(newPos!==null){updateValues();inp.setSelectionRange(newPos,newPos);}
    inp.focus();
  });
  bar.appendChild(clrBtn);
  el.appendChild(bar);

  const inputs=[];
  const labels=model.get('labels')||[];
  const initVals=model.get('values')||[];

  // shared by keydown-Enter and mobile "Go" (form submit) below — idx is
  // -1 (submit_request.field_index's own documented "unset" default) when
  // nothing was focused; fireSubmit skips locking/pendingOrigin entirely
  // for it below, so change:focus_request's reply naturally finds no
  // origin to act on instead of needing its own -1 check.
  function fireSubmit(idx){
    // Already locked (a reply for this field is still in flight) -- a
    // repeat Enter/"Go" while waiting can't mean anything new since the
    // field is read-only and hasn't changed, so drop it instead of piling
    // up a second concurrent request for the same field.
    if(idx>=0&&idx<inputs.length&&inputs[idx].readOnly)return;
    clearTimeout(_debTimer);
    flushValues();
    const reqId=(model.get('submit_request').request_id||0)+1;
    if(idx>=0&&idx<inputs.length){
      // Lock the field the instant Enter fires. Python's validation is a
      // real async round trip (a full reactive-cell rerun); without this,
      // an impatient typist's next keystrokes land in this still-focused
      // field instead of waiting -- which was the actual cause of both
      // "focus jumps to a stale field" and "my typing erases itself" (a
      // late .select() landing mid-keystroke). Released the moment the
      // reply for reqId comes back, or after 3s as a backstop in case a
      // reply never arrives for this exact request.
      inputs[idx].readOnly=true;
      pendingOrigin.set(reqId,idx);
      setTimeout(()=>{
        if(pendingOrigin.delete(reqId))releaseLock(idx);
      },3000);
    }
    // request_id and field_index only ever mean something together (a
    // count with no origin field, or vice versa, is meaningless here), so
    // one Dict trait replaces what used to be two separate Int traits --
    // both fields land in the same model.set() call, with no window where
    // a listener could see one updated but not the other. Deliberately NOT
    // merged further with focus_request into a single bidirectional trait:
    // model.set() fires this same client's own change: handlers
    // synchronously (confirmed empirically), so a trait written by both
    // sides would need explicit self-echo detection that submit_request
    // (JS-only writer) and focus_request (Python-only writer) each avoid
    // by construction.
    model.set('submit_request',{request_id:reqId,field_index:idx});
    model.save_changes();
  }

  // form submit handles mobile "Go" button (doesn't fire keydown 'Enter')
  const form=document.createElement('form');
  form.style.display='contents';
  form.addEventListener('submit',e=>{
    e.preventDefault();
    fireSubmit(inputs.indexOf(focusedInp));
  });

  labels.forEach((lbl,i)=>{
    const row=document.createElement('div');
    row.className='eee-para-row';
    const lblEl=document.createElement('span');
    lblEl.className='eee-para-lbl';
    lblEl.textContent=lbl;
    const inp=document.createElement('input');
    inp.type='text';
    inp.className='eee-para-inp';
    inp.value=initVals[i]||'';
    inp.addEventListener('focus',()=>{focusedInp=inp;});
    inp.addEventListener('keydown',e=>{
      if(e.key!=='Enter')return;
      e.preventDefault();
      fireSubmit(i);
    });
    inp.addEventListener('beforeinput',e=>{
      biSnap=null;
      // readOnly blocks the browser's own native text insertion, but this
      // handler bypasses that entirely with its own preventDefault()+manual
      // inp.value= assignment below -- readOnly must be checked explicitly
      // here too, or a locked field can still be edited via diacritic
      // mark composition even though plain typing is correctly blocked.
      if(inp.readOnly)return;
      if(!activeMarks.size||(e.inputType!=='insertText'&&e.inputType!=='insertCompositionText')||!e.data)return;
      const base=e.data.normalize('NFD')[0];
      if(!VOWELS.has(base)){clearAllMarks(activeMarks);return;}
      const marks=getMarksFor(activeMarks,base);
      if(!marks)return;
      e.preventDefault();
      const s=inp.selectionStart??inp.value.length,end=inp.selectionEnd??s;
      const composed=(base+marks).normalize('NFC');
      inp.value=inp.value.slice(0,s)+composed+inp.value.slice(end);
      inp.setSelectionRange(s+composed.length,s+composed.length);
      biSnap={inp,value:inp.value,pos:s+composed.length};
      updateValues();
    });
    inp.addEventListener('input',()=>{
      if(biSnap&&biSnap.inp===inp){
        inp.value=biSnap.value;inp.setSelectionRange(biSnap.pos,biSnap.pos);biSnap=null;
        updateValues();return;
      }
      updateValues();
    });
    row.appendChild(lblEl);row.appendChild(inp);
    form.appendChild(row);
    inputs.push(inp);
  });
  el.appendChild(form);

  // Unlike the beforeinput/clrBtn guards above, this one doesn't need its
  // own readOnly check: values is only ever written by flushValues() below
  // (client -> server), so a change:values event is always an echo of data
  // this same client just sent -- reapplying it to a locked field re-sets
  // the same value already there, never a surprising external overwrite.
  model.on('change:values',()=>{
    const vals=model.get('values')||[];
    inputs.forEach((inp,i)=>{if(inp.value!==(vals[i]||''))inp.value=vals[i]||'';});
  });

  model.on('change:focus_request',()=>{
    const{request_id,advance_to}=model.get('focus_request')||{};
    const originIdx=pendingOrigin.get(request_id);
    // No locked field matches this reply (nothing was focused when Enter
    // fired, so fireSubmit never locked or recorded an origin for it) --
    // nothing to unlock or apply.
    if(originIdx===undefined)return;
    pendingOrigin.delete(request_id);
    releaseLock(originIdx);
    // A newer Enter has been sent since this reply was computed -- it's
    // for a request that's no longer the latest, so don't act on it.
    if(request_id!==(model.get('submit_request').request_id||0))return;
    // The user has manually moved away (click/tab) from the origin field
    // since submitting -- respect that instead of yanking focus back.
    if(focusedInp!==inputs[originIdx])return;
    // advance_to is null on a wrong answer or the last field -- this reply
    // exists only to release the lock, there's nowhere to move focus to.
    if(advance_to!=null&&advance_to<inputs.length){inputs[advance_to].focus();inputs[advance_to].select();}
  });
}
export default{render};
"""


if _ANYWIDGET_OK:
    class _ParadigmFormWidget(_anywidget.AnyWidget):
        _css = _PARA_CSS
        _esm = _PARA_ESM
        labels = _traitlets.List(_traitlets.Unicode()).tag(sync=True)
        values = _traitlets.List(_traitlets.Unicode()).tag(sync=True)
        submit_request = _traitlets.Dict().tag(sync=True)
        focus_request = _traitlets.Dict().tag(sync=True)
        polytonic = _traitlets.Bool(True).tag(sync=True)


def make_paradigm_form(mo, labels, values=None, polytonic=True):
    """Multi-input paradigm drill form with a shared diacritics bar.

    Returns a ``mo.ui.anywidget`` whose ``.widget.values`` is a list of strings
    (one per label), suitable for verb/noun paradigm exercises.
    Requires ``anywidget``.

    ``values``: optional pre-fill, one string per label (e.g. to restore
    what was previously typed for this word when navigating back to it).
    Defaults to blank fields. Length must match ``labels`` if given.

    ``polytonic``: ``True`` (default) shows the full mark set (acute, grave,
    circumflex, rough/smooth breathing, iota subscript, diaeresis) for Ancient
    Greek. ``False`` shows only acute accent and diaeresis — the two marks
    Modern Greek's monotonic orthography actually uses; breathing marks and
    iota subscript were dropped in the 1982 reform, so offering them for
    Modern Greek content is confusing, not just unnecessary. Pass
    ``config.polytonic`` (from :class:`GreekConfig`) rather than hardcoding.

    Pressing Enter in any field (desktop keydown, or a mobile virtual
    keyboard's "Go"/submit action — both wired) flushes the current values
    immediately (no debounce wait) and sets
    ``.widget.submit_request = {"request_id": seq, "field_index": idx}``
    (``field_index`` is ``-1`` if none was focused) — treat a new
    ``request_id`` as an additional "check" trigger alongside a submit
    button, the same way the button's own click counter is watched. The
    triggering field is locked read-only client-side until a reply comes
    back (see below), so it can't take an "advance was correct — jump
    here" reply based on a value the user already changed again.

    Set ``.widget.focus_request = {"request_id": seq, "advance_to": index}``
    (pair ``request_id`` with ``submit_request["request_id"]`` — both to
    guarantee change-detection and because the JS side matches it against
    the request it's still waiting on; a reply for any other ``request_id``
    is superseded) to move focus to a field programmatically — e.g. to the
    next field after confirming the current one is correct via a per-slot
    check. Reply on *every* Enter, including a wrong answer or the last
    field (``advance_to=None``) — the field stays locked until its exact
    ``request_id`` gets a reply, so a reply that only unlocks and moves
    nowhere is still required.
    """
    if not _ANYWIDGET_OK:
        raise ImportError("anywidget is required for make_paradigm_form")
    w = _ParadigmFormWidget()
    w.labels = list(labels)
    w.values = list(values) if values is not None else [""] * len(labels)
    w.polytonic = polytonic
    return mo.ui.anywidget(w)


# ════════════════════════════════════════ interactive text (clickable words) ══

_ITEXT_CSS = """\
.eee-itext{font-family:'Gentium Plus','GFS Didot',serif;font-size:1.15em;line-height:2}
.eee-itext .gk-word{cursor:pointer;border-bottom:1px dotted #7a7a7a;padding-bottom:0}
.eee-itext .gk-word:hover{border-bottom-color:#003d82}
.eee-itext .gk-word:focus{outline:2px solid #003d82;outline-offset:1px}
.eee-itext .gk-word.homer{background:#f2ecd8}
.eee-itext .gk-word.active{background:#dceeff;border-bottom:2px solid #003d82}
"""

# Tokenizer/normalizer mirror norm_grc_surface (strip_diacritics + strip
# "',.··᾽᾿ʼ", including both the middle dot U+00B7 and Greek ano teleia
# U+0387) so a rendered token's key matches a `clickable` set built by that
# function (e.g. via the public grc_coverage_words(..., mode="none", ...)) --
# NOT the pilot notebook's separate _norm/_bare pair, which strips a
# different punctuation set.
_ITEXT_ESM = r"""
const EDGE_PUNCT = /^[',.··᾽᾿ʼ]+|[',.··᾽᾿ʼ]+$/g;

function normKey(text) {
  return text.replace(EDGE_PUNCT, '')
    .normalize('NFD').replace(/[̀-ͯ]/g, '').normalize('NFC');
}

function bareText(html) {
  let text = '', inTag = false;
  for (const ch of html) {
    if (ch === '<') inTag = true;
    else if (ch === '>') inTag = false;
    else if (!inTag) text += ch;
  }
  return text.replace(EDGE_PUNCT, '');
}

function splitTokens(html) {
  const tokens = [];
  let buf = '', depth = 0;
  for (const ch of html) {
    if (ch === '<') { depth++; buf += ch; }
    else if (ch === '>') { depth--; buf += ch; }
    else if (ch === ' ' && depth === 0) { if (buf) tokens.push(buf); buf = ''; }
    else buf += ch;
  }
  if (buf) tokens.push(buf);
  return tokens;
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function render({ model, el }) {
  const container = document.createElement('div');
  container.className = 'eee-itext';

  function draw() {
    const lines = model.get('lines') || [];
    const clickableSet = new Set(model.get('clickable') || []);
    const homerSet = new Set(model.get('homer_words') || []);
    const showIctus = model.get('show_ictus');
    const ictusHtml = model.get('ictus_html') || {};
    const selected = model.get('selected_word') || '';

    const lineHtml = lines.map(line => {
      // ictusHtml values are trusted, internally-authored markup (e.g. <b>
      // ictus spans) and must render as-is; a plain `line` is guaranteed
      // tag-free, so its tokens are safe (and, per stray-character defense,
      // required) to HTML-escape before display.
      const trusted = showIctus && ictusHtml[line];
      const source = trusted || line;
      const parts = splitTokens(source).map(tok => {
        const bare = bareText(tok);
        const key = normKey(bare);
        const display = trusted ? tok : escapeHtml(tok);
        if (!clickableSet.has(key)) return display;
        const activeCls = bare === selected ? ' active' : '';
        const homerCls = homerSet.has(key) ? ' homer' : '';
        return `<span class="gk-word${homerCls}${activeCls}" role="button" tabindex="0" data-w="${escapeHtml(bare)}">${display}</span>`;
      });
      return parts.join(' ');
    });

    container.innerHTML = lineHtml.join('<br>');
  }

  function activate(span) {
    model.set('selected_word', span.dataset.w);
    model.set('click_seq', (model.get('click_seq') || 0) + 1);
    model.save_changes();
    draw();
  }

  container.addEventListener('click', e => {
    const span = e.target.closest('.gk-word');
    if (span) activate(span);
  });
  container.addEventListener('keydown', e => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const span = e.target.closest('.gk-word');
    if (!span) return;
    e.preventDefault();
    activate(span);
  });

  // Python swapping lines/clickable/homer_words/show_ictus/ictus_html must
  // redraw so the new content (and the persisted .active highlight) render.
  // selected_word and click_seq are JS-write/Python-read only (set
  // exclusively by activate(), which already redraws explicitly) — no
  // listener needed for them, and adding one would double-draw every click.
  model.on('change:lines', draw);
  model.on('change:clickable', draw);
  model.on('change:homer_words', draw);
  model.on('change:show_ictus', draw);
  model.on('change:ictus_html', draw);

  draw();
  el.appendChild(container);
}
export default { render };
"""


if _ANYWIDGET_OK:
    class _InteractiveTextWidget(_anywidget.AnyWidget):
        _css = _ITEXT_CSS
        _esm = _ITEXT_ESM
        lines = _traitlets.List(_traitlets.Unicode()).tag(sync=True)
        clickable = _traitlets.List(_traitlets.Unicode()).tag(sync=True)
        homer_words = _traitlets.List(_traitlets.Unicode()).tag(sync=True)
        ictus_html = _traitlets.Dict().tag(sync=True)
        show_ictus = _traitlets.Bool(True).tag(sync=True)
        selected_word = _traitlets.Unicode("").tag(sync=True)
        click_seq = _traitlets.Int(0).tag(sync=True)


def interactive_text(mo, *, lines, clickable, homer_words=None, ictus_html=None, show_ictus=True) -> Any:
    """Render poem `lines` with vocabulary words as permanent clickable spans.

    Returns the real ``mo.ui.anywidget`` — a panel cell must reference
    ``.widget.selected_word`` (bumped alongside ``.widget.click_seq`` on every
    click, including repeat-clicks on the same word) to re-run when a word is
    clicked. Requires ``anywidget``.

    ``clickable``: an iterable of normalized surface forms (as produced by
    :func:`grc_coverage_words`, e.g. with ``mode="none"`` for "all words", or
    directly via :func:`norm_grc_surface`) — a rendered token is clickable
    when its own normalized form (mirroring :func:`norm_grc_surface`) is a
    member.

    ``homer_words``: optional iterable of normalized surface forms (e.g.
    :func:`grc_coverage_words` with ``mode="homer"``) — a clickable token
    whose normalized form is a member gets an extra ``.homer`` CSS class
    (background highlight), signaling the word-form table for this exact
    attested form is confirmed by the Homeric corpus lexicon specifically,
    not just reachable via some lexicon in the combined engine.

    ``ictus_html``: optional ``{raw_line: html_with_markup}`` map; shown per
    line when ``show_ictus`` is true, else the plain line text.
    """
    if not _ANYWIDGET_OK:
        raise ImportError("anywidget is required for interactive_text")
    w = _InteractiveTextWidget()
    w.lines = list(lines)
    w.clickable = list(clickable)
    w.homer_words = list(homer_words) if homer_words else []
    w.ictus_html = dict(ictus_html) if ictus_html else {}
    w.show_ictus = bool(show_ictus)
    return mo.ui.anywidget(w)


def add_labels(words: list[dict]) -> None:
    """Set word["_label"] from context + meaning, in place, for each word dict.

    "{context} – {meaning}" when context is present, else "«{meaning}»".
    """
    for w in words:
        ctx = w.get("context", "")
        meaning = w.get("meaning", "")
        w["_label"] = f"{ctx} – {meaning}" if ctx else f"«{meaning}»"


def _lemma_of(word: dict, form: str) -> str:
    """Return word["lemma"], falling back to the already-resolved form when absent.

    See the "form vs. lemma" note in docs/api-patterns.md — lemma is the
    dictionary/citation form, absent for flat vocab where it equals form.
    """
    return word.get("lemma", form)


# ancient_greek_backend_eee's pronoun-tags.tsv legitimately has multiple
# rows sharing the same tag string across pronoun families (e.g. .NSM is
# used by both a demonstrative and a relative pronoun, each with a
# different PronType) -- PronType is a per-lemma-family fact layered onto
# an otherwise POS-level (not lemma-level) tag table. resolve_word_grammar
# must filter by the word's own lemma before doing first-tag-match, or it
# always resolves to whichever PronType happens to sort first for a
# shared tag (found in section-05's code review, 2026-07-12 -- see
# ancient_greek_backend_eee/tools/generate_pronoun_tags.py for the full
# reasoning on the producing side). A second hardcoded table here (rather
# than asking the backend) is a deliberate, closed-class-sized tradeoff:
# only 10 pronoun lemmas exist, cheap to keep in sync manually; mirrors
# tools/generate_pronoun_tags.py's own _PRONTYPE dict verbatim.
_PRON_TYPE = {
    "ἐγώ": "Prs", "σύ": "Prs",
    "οὗτος": "Dem", "ἐκεῖνος": "Dem", "ὅδε": "Dem",
    "ὅς": "Rel",
    "τίς": "Int",
    "τις": "Ind",  # accent-only minimal pair with τίς -- a genuinely
                    # distinct lemma, not the same key normalized
    "ὅστις": "Rel",
    "ἀλλήλων": "Rcp",
}


# ════════════════════════════════════════ greek comparison utils ══

def strip_diacritics(s: str) -> str:
    """Remove diacritical marks (NFD decompose then drop Unicode category Mn).

    Works for both Modern (monotonic) and Ancient (polytonic) Greek.

    Example::

        strip_diacritics("λέγε") == "λεγε"  # True
    """
    return "".join(
        c for c in _unicodedata.normalize("NFD", s)
        if _unicodedata.category(c) != "Mn"
    )


# codepoint groups for polytonic → monotonic normalization
_PTM_DROP = {"\u0313", "\u0314", "\u0345"}             # psili, dasia, iota subscript
_PTM_REMAP = {"\u0300": "\u0301", "\u0342": "\u0301"}  # varia, perispomeni → tonos


def poly_to_mono(text: str) -> str:
    """Normalize polytonic Ancient Greek to monotonic Modern Greek.

    NFD-decompose; drop breathings (psili U+0313, dasia U+0314) and the iota
    subscript (U+0345); remap grave (U+0300) and circumflex (U+0342) to the tonos
    (acute, U+0301); keep tonos and diaeresis (U+0308); NFC-recompose.

    Unlike :func:`strip_diacritics` (which drops *all* marks to make an unaccented
    key), this preserves stress — it turns a curated polytonic Ancient lemma into
    the monotonic lemma the Modern-Greek backend expects. Does NOT apply final-sigma
    (σ→ς) or the monosyllable-tonos-drop rule (separate concerns, not needed for
    polysyllabic paradigm-cell display). Idempotent on already-monotonic input.

    Example::

        poly_to_mono("ἄνθρωπος") == "άνθρωπος"   # True
    """
    out = []
    for c in _unicodedata.normalize("NFD", text):
        if _unicodedata.combining(c):
            if c in _PTM_DROP:
                continue
            out.append(_PTM_REMAP.get(c, c))
        else:
            out.append(c)
    return _unicodedata.normalize("NFC", "".join(out))


def parse_stanza_text(md: str, *, ref_prefix: str = "### ") -> dict:
    """Parse a ``greek.md``-style poem source file into ``{stanza_ref: [lines]}``.

    A ``<ref_prefix><ref>`` heading (e.g. ``"### Odyss. IX.39-42"`` with
    ``ref_prefix="### Odyss. "``, or ``"### Ithaki 1-3"`` with the default
    ``"### "``) opens a new stanza; every non-blank line under it, up to the
    next such heading, is one poem line, in order. Lines starting ``<!--``
    (an HTML comment, e.g. a source citation) are skipped everywhere, not
    just before the first heading.

    Was duplicated near-identically across every Odyssey lesson notebook
    (each with its own module-local ``_parse_greek``) before being extracted
    here — ``ref_prefix`` is the one thing that varied between callers.
    """
    out, ref, buf = {}, None, []
    def _flush():
        if ref:
            out[ref] = buf
    for L in md.splitlines():
        if L.startswith(ref_prefix):
            _flush()
            ref, buf = L[len(ref_prefix):].strip(), []
        elif ref and L.strip() and not L.startswith("<!--"):
            buf.append(L.strip())
    _flush()
    return out


def parse_stanza_translations(md: str, *, ref_prefix: str = "### ") -> "tuple[dict, dict]":
    """Parse a ``translations.md``-style file into ``({translator: {stanza_ref: text}}, {translator: description})``.

    ``## <name>`` opens a translator's section (e.g. ``"## подстрочник"``,
    ``"## Жуковский"``). An optional ``<!-- **...** -->`` comment line right
    after a ``## <name>`` heading (before any ``<ref_prefix><ref>`` heading)
    becomes that translator's ``description`` entry — omit it for a
    translator like подстрочник that gets its description handled specially
    by the caller instead. ``<ref_prefix><ref>`` (matching :func:`parse_stanza_text`'s
    own ``ref_prefix``) opens a stanza within the current translator's
    section; every following line up to the next heading or a bare ``---``
    separator is joined with ``\\n`` into that stanza's translation text —
    the block must have exactly as many lines as :func:`parse_stanza_text`'s
    matching stanza, in the same order, since callers zip them positionally.

    Was duplicated near-identically across every Odyssey lesson notebook
    (each with its own module-local ``_parse_trans``) before being extracted
    here — ``ref_prefix`` is the one thing that varied between callers.
    """
    out, desc, tr, ref, buf = {}, {}, None, None, []
    def _flush():
        if tr and ref and buf:
            out.setdefault(tr, {})[ref] = "\n".join(buf)
    for L in md.splitlines():
        if L.startswith("## "):
            _flush()
            tr, ref, buf = L[3:].strip(), None, []
        elif tr and ref is None and L.startswith("<!-- **") and L.endswith("-->"):
            desc[tr] = L[4:-3].strip()
        elif L.startswith(ref_prefix):
            _flush()
            ref, buf = L[len(ref_prefix):].strip(), []
        elif ref and L.strip() and L.strip() != "---":
            buf.append(L)
    _flush()
    return out, desc


def greek_compare(
    a: str,
    b: str,
    *,
    case_sensitive: bool = False,
    diacritics: bool = False,
) -> bool:
    """Compare two Greek strings with configurable normalization.

    Works for both Modern and Ancient Greek.

    Args:
        case_sensitive: If ``False`` (default), comparison ignores case.
        diacritics:     If ``False`` (default), diacritical marks are stripped
                        before comparison. If ``True``, NFC-normalized forms
                        must match exactly (including accents).

    Example::

        greek_compare("λεγε", "λέγε")                        # True
        greek_compare("λεγε", "λέγε", diacritics=True)       # False
        greek_compare("Λέγε", "λέγε", case_sensitive=True)   # False
    """
    def _norm(s: str) -> str:
        s = s.strip()
        if not diacritics:
            s = strip_diacritics(s)
        else:
            s = _unicodedata.normalize("NFC", s)
        if not case_sensitive:
            s = s.lower()
        return s
    return _norm(a) == _norm(b)


# ════════════════════════════════════════════════════ greek configs ══


@dataclass
class GreekConfig:
    """Language-period config for GreekUtils quiz widgets.

    Pass ``config=ANCIENT_GREEK`` to ``GreekUtils(backend, mo, pd, config=...)``
    to switch between Modern and Ancient Greek exercise conventions.
    """
    language: str                       # EEE language code ("el", "grc")
    articles: "dict | None"             # definite articles by gender/num/case
    indef_articles: "dict | None"       # indefinite articles; None = not used
    noun_cells: "list[tuple[str,str]]"  # (num, case) slots per noun exercise
    tense_feats: dict                   # tense_key → UD feature dict
    tense_labels: dict                  # tense_key → {"greek": ..., "label": {"en"/"ru"/"el": ...}}
    path_map: dict                      # tense_key → paradigm() key (backend fallback)
    verb_prefix: dict                   # tense_key → particle string (e.g. "θα")
    verb_slots: "list[tuple[str,str]]"  # (num, person) slots per verb exercise
    verb_labels: "list[str]"            # display label per verb slot
    adj_cases: "list[str]"              # cases for full adjective paradigm
    compare_diacritics: bool            # default diacritics flag for _ci
    polytonic: bool                     # show breathing/subscript/diaeresis marks in make_paradigm_form's bar, not just the acute accent


# ─────────────────────────────────────────────────── article tables ──

_ARTS = {
    'masc': {'sg': {'nom': {'ο'}, 'acc': {'τον'}, 'gen': {'του'}},
             'pl': {'nom': {'οι'}, 'acc': {'τους'}, 'gen': {'των'}}},
    'fem':  {'sg': {'nom': {'η'}, 'acc': {'την', 'τη'}, 'gen': {'της'}},
             'pl': {'nom': {'οι'}, 'acc': {'τις'}, 'gen': {'των'}}},
    'neut': {'sg': {'nom': {'το'}, 'acc': {'το'}, 'gen': {'του'}},
             'pl': {'nom': {'τα'}, 'acc': {'τα'}, 'gen': {'των'}}},
}

_IARTS = {
    'masc': {'sg': {'nom': {'ένας'}, 'acc': {'ένα', 'έναν'}, 'gen': {'ενός'}}},
    'fem':  {'sg': {'nom': {'μια', 'μία'}, 'acc': {'μια', 'μία'}, 'gen': {'μιας', 'μίας'}}},
    'neut': {'sg': {'nom': {'ένα'}, 'acc': {'ένα'}, 'gen': {'ενός'}}},
}

_AG_ARTS = {
    'masc': {
        'sg': {'nom': {'ὁ'},  'acc': {'τόν', 'τὸν'}, 'gen': {'τοῦ'}, 'dat': {'τῷ'}},
        'pl': {'nom': {'οἱ'}, 'acc': {'τούς', 'τοὺς'}, 'gen': {'τῶν'}, 'dat': {'τοῖς'}},
    },
    'fem': {
        'sg': {'nom': {'ἡ'},  'acc': {'τήν', 'τὴν'}, 'gen': {'τῆς'}, 'dat': {'τῇ'}},
        'pl': {'nom': {'αἱ'}, 'acc': {'τάς', 'τὰς'}, 'gen': {'τῶν'}, 'dat': {'ταῖς'}},
    },
    'neut': {
        'sg': {'nom': {'τό'}, 'acc': {'τό'}, 'gen': {'τοῦ'}, 'dat': {'τῷ'}},
        'pl': {'nom': {'τά'}, 'acc': {'τά'}, 'gen': {'τῶν'}, 'dat': {'τοῖς'}},
    },
}

# ─────────────────────────────── UD feature tables (language-agnostic) ──

_CASE   = {'nom': 'Nom', 'acc': 'Acc', 'gen': 'Gen', 'dat': 'Dat', 'voc': 'Voc'}
_NUM    = {'sg': 'Sing', 'pl': 'Plur', 'du': 'Dual'}
_GENDER = {'masc': 'Masc', 'fem': 'Fem', 'neut': 'Neut'}
_PERSON = {'pri': '1', 'sec': '2', 'ter': '3'}

# ──────────────────────────── quiz display labels (noun/adjective UI) ──

_QUIZ_NUM_LABEL    = {'sg': 'Sg.', 'pl': 'Pl.', 'du': 'Du.'}
_QUIZ_CASE_LABEL   = {'nom': 'Nom.', 'acc': 'Acc.', 'gen': 'Gen.', 'dat': 'Dat.', 'voc': 'Voc.'}
_QUIZ_ADJ_GENDER   = {'masc': 'Masc', 'fem': 'Fem', 'neut': 'Neut'}
_QUIZ_ADJ_NUM      = {'sg': 'Sg', 'pl': 'Pl'}

# ────────────────────────────────────────────── tense / verb tables ──

def _load_tense_labels(config_key: str) -> dict:
    """Load tense_labels for one GreekConfig ('modern_greek'/'ancient_greek') from
    the bundled eee_project.data.labels/tense-{lang}.tsv files -- translated tense
    names live in the TSVs (same routing layer as noun/adj/verb slot labels), never
    hardcoded in this module.
    """
    pkg = importlib.resources.files("eee_project.data.labels")
    per_tense: dict = {}
    for lang in ("en", "ru", "el"):
        text = (pkg / f"tense-{lang}.tsv").read_text(encoding="utf-8")
        for row in csv.DictReader(text.splitlines(), delimiter="\t"):
            if row["Config"] != config_key:
                continue
            per_tense.setdefault(row["Tense"], {})[lang] = row["label"]
    return {tense: {"greek": langs["el"], "label": langs} for tense, langs in per_tense.items()}


def _load_ui_labels() -> dict:
    """Load widget-chrome UI strings (headings, button labels, empty-state text)
    from the bundled eee_project.data.labels/ui-{lang}.tsv files -- same routing
    layer as tense/noun/adj/verb labels, never hardcoded in a notebook. Not
    Config-scoped (unlike tense_labels) since this text belongs to the shared
    paradigm-drill widget chrome, not any one course's grammar.
    """
    pkg = importlib.resources.files("eee_project.data.labels")
    labels: dict = {}
    for lang in ("en", "ru", "el"):
        text = (pkg / f"ui-{lang}.tsv").read_text(encoding="utf-8")
        for row in csv.DictReader(text.splitlines(), delimiter="\t"):
            labels.setdefault(row["Key"], {})[lang] = row["label"]
    return labels


_UI_LABELS = _load_ui_labels()


_MG_TENSE_FEATS = {
    'present':           {'Tense': 'Pres', 'Mood': 'Ind'},
    'imperfect':         {'Tense': 'Past', 'Aspect': 'Imp',  'Mood': 'Ind'},
    'aorist':            {'Tense': 'Past', 'Aspect': 'Perf', 'Mood': 'Ind'},
    'future':            {'Tense': 'Fut',  'Aspect': 'Perf', 'Mood': 'Ind'},
    'future_continuous': {'Tense': 'Fut',  'Aspect': 'Imp',  'Mood': 'Ind'},
}
_MG_PATH_MAP = {
    'present':           'present',
    'imperfect':         'paratatikos',
    'aorist':            'aorist',
    'future':            'conjunctive',
    'future_continuous': 'present',
}
_AG_TENSE_FEATS = {
    'present':   {'VerbForm': 'Fin', 'Tense': 'Pres', 'Mood': 'Ind'},
    'imperfect': {'VerbForm': 'Fin', 'Tense': 'Past', 'Aspect': 'Imp',  'Mood': 'Ind'},
    'aorist':    {'VerbForm': 'Fin', 'Tense': 'Past', 'Aspect': 'Perf', 'Mood': 'Ind'},
    'perfect':   {'VerbForm': 'Fin', 'Tense': 'Pqp',  'Aspect': 'Perf', 'Mood': 'Ind'},
    'future':    {'VerbForm': 'Fin', 'Tense': 'Fut',  'Mood': 'Ind'},
}

_VERB_SLOTS = [('sg', 'pri'), ('sg', 'sec'), ('sg', 'ter'),
               ('pl', 'pri'), ('pl', 'sec'), ('pl', 'ter')]

# ───────────────────────────────────────────────── config instances ──

MODERN_GREEK = GreekConfig(
    language='el',
    articles=_ARTS,
    indef_articles=_IARTS,
    noun_cells=[
        ('sg', 'nom'), ('sg', 'acc'), ('sg', 'gen'),
        ('pl', 'nom'), ('pl', 'acc'), ('pl', 'gen'),
    ],
    tense_feats=_MG_TENSE_FEATS,
    tense_labels=_load_tense_labels('modern_greek'),
    path_map=_MG_PATH_MAP,
    verb_prefix={'future': 'θα', 'future_continuous': 'θα'},
    verb_slots=_VERB_SLOTS,
    verb_labels=['εγώ', 'εσύ', 'αυτός,-ή,-ό', 'εμείς', 'εσείς', 'αυτοί,-ές,-ά'],
    adj_cases=['nom', 'acc', 'gen'],
    compare_diacritics=True,
    polytonic=False,
)

ANCIENT_GREEK = GreekConfig(
    language='grc',
    articles=_AG_ARTS,
    indef_articles=None,
    noun_cells=[
        ('sg', 'nom'), ('sg', 'acc'), ('sg', 'gen'), ('sg', 'dat'),
        ('pl', 'nom'), ('pl', 'acc'), ('pl', 'gen'), ('pl', 'dat'),
    ],
    tense_feats=_AG_TENSE_FEATS,
    tense_labels=_load_tense_labels('ancient_greek'),
    path_map={},
    verb_prefix={},
    verb_slots=_VERB_SLOTS,
    verb_labels=['1 sg', '2 sg', '3 sg', '1 pl', '2 pl', '3 pl'],
    adj_cases=['nom', 'acc', 'gen', 'dat'],
    compare_diacritics=True,
    polytonic=True,
)


def setup_ancient_greek(backend: Any) -> None:
    """Register *backend* as the Ancient Greek backend and activate the chain.

    Equivalent to the three-line boilerplate used in every AG notebook::

        eee.register_backend("grc", ag)
        eee.register_backend("grc", ag, backend="ancient-greek")
        eee.set_chain("grc", ["ancient-greek"])
    """
    register_backend("grc", backend)
    register_backend("grc", backend, backend="ancient-greek")
    set_chain("grc", ["ancient-greek"])


# Two DIFFERENT, independent sets used by the Odyssey lesson notebooks --
# easy to conflate (a past session's stale-kernel save silently reverted one
# while editing the other). LEXICON_TAG_POS controls which words get a
# lexicon-coverage badge computed at all; TRANSLATION_PRESENCE_CONTENT_POS
# controls which words are eligible for the "слово в переводе" exercise.
# Changing one never implies changing the other.

# POS values eligible for a "which lexicon confirms this exact attested
# form" coverage badge (see the per-notebook `_lexicon_tag` helper).
LEXICON_TAG_POS = {"noun", "verb", "adj", "pronoun"}

# Short POS code -> the string form/paradigm-lookup functions expect,
# for the POS values in LEXICON_TAG_POS that don't already match
# (only "adj" needs remapping; the others are already spelled correctly).
LEXICON_TAG_POS_ALIASES = {"adj": "adjective"}

# POS values treated as "content words" for the translation-presence
# exercise -- function words (particles, conjunctions, prepositions,
# pronouns) are excluded by design: "is this function word reflected"
# isn't a meaningful question for a literary translation.
TRANSLATION_PRESENCE_CONTENT_POS = {"noun", "verb", "adj", "adv", "name"}


class GreekUtils:
    """Marimo notebook helper for Greek noun/verb/adjective quiz cells."""

    def __init__(self, backend: Any = None, mo_module: Any = None, pd_module: Any = None,
                 eee_module: Any = None,
                 config: GreekConfig = MODERN_GREEK) -> None:
        self._mg = backend
        self._mo = mo_module
        self._pd = pd_module
        self._eee = eee_module
        self._cfg = config
        self._paradigm_cache: dict = {}
        self._eee_forms_cache: dict = {}

    @property
    def TENSE_LABELS(self) -> dict:
        return self._cfg.tense_labels

    def tense_dropdown_options(self, lang: str = "en") -> dict:
        """Localized ``{"Continuous Future (Συνεχής Μέλλοντας)": "future_continuous", ...}``
        options dict for a verb-tense-selector dropdown, keyed by ``tense_labels``'
        insertion order (present/imperfect/aorist/future/... as configured).
        Falls back to English if ``lang`` has no entry for a given tense. Drops the
        parenthetical Greek reference when it's already the label (``lang="el"``) --
        "Ενεστώτας (Ενεστώτας)" would just be a redundant echo of itself.
        """
        out = {}
        for key, info in self._cfg.tense_labels.items():
            label = info['label'].get(lang, info['label']['en'])
            display = label if label == info['greek'] else f"{label} ({info['greek']})"
            out[display] = key
        return out

    def ui_label(self, key: str, lang: str | None = None) -> str:
        """Translated paradigm-drill widget-chrome string (heading, button
        label, empty-state text) for ``key``, backed by
        ``data/labels/ui-{lang}.tsv``. Falls back to English if ``lang`` has
        no entry, then to the bare ``key`` if the key itself is unknown --
        same fallback shape as the notebook-local ``t_ui()`` helper this
        replaces. Not Config-scoped (unlike :meth:`tense_dropdown_options`)
        since this text belongs to the shared widget, not one course's
        grammar -- assign ``t_ui = gu2.ui_label`` in a notebook to keep every
        existing ``t_ui("key", lang)`` call site unchanged.
        """
        lang = lang or "en"
        entry = _UI_LABELS.get(key, {})
        return entry.get(lang) or entry.get("en") or key

    # ------------------------------------------------------------------ utils

    def _paradigm(self, word: str, pos: str) -> dict:
        """Backend paradigm lookup, memoized per (word, pos) for this instance.

        Callers (_noun_forms/_verb_forms/_adj_forms/...) invoke this once per
        grammatical cell being checked/rendered — the same (word, pos) recurs
        many times per word (e.g. once per case/number/gender combination).
        """
        key = (word, pos)
        if key not in self._paradigm_cache:
            try:
                self._paradigm_cache[key] = self._mg.paradigm(word, pos)
            except Exception:
                self._paradigm_cache[key] = {}
        return self._paradigm_cache[key]

    def _ci(self, value: str, forms) -> bool:
        if not forms:
            return False
        # expand "form(x)" optional-suffix notation (e.g. λύουσι(ν) → λύουσι + λύουσιν)
        expanded: set = set()
        for f in forms:
            expanded.add(f)
            i = f.find('(')
            if i != -1 and f.endswith(')'):
                base, opt = f[:i], f[i+1:-1]
                expanded.add(base)
                expanded.add(base + opt)
        return any(
            greek_compare(value, f, case_sensitive=False,
                          diacritics=self._cfg.compare_diacritics)
            for f in expanded
        )

    # -------------------------------------------------------- slot-based helpers

    def _eee_forms(self, word: str, pos: str, features: dict) -> set | None:
        """Inflect via eee.inflect_slot(); None when no eee module was provided.

        Memoized per (word, pos, features) for this instance — the per-slot
        checkers (check_verb_slot/check_noun_slot, called once per Enter
        press) and the full-form checkers (check_verb_test/check_noun_test,
        called on submit) resolve the same slots for the same word, so
        without this cache a submit re-queries the backend for every slot
        already resolved via Enter.
        """
        if self._eee is None:
            return None
        key = (word, pos, tuple(sorted(features.items())))
        if key not in self._eee_forms_cache:
            slot = SlotTemplate(tag_type="ud", label="", features=features)
            try:
                self._eee_forms_cache[key] = self._eee.inflect_slot(word, slot, pos, language=self._cfg.language)
            except Exception:
                self._eee_forms_cache[key] = set()
        return self._eee_forms_cache[key]

    def _noun_forms(self, word: str, num: str, case: str) -> set:
        forms = self._eee_forms(word, "noun", {"Case": _CASE[case], "Number": _NUM[num]})
        if forms is not None:
            return forms
        p = self._paradigm(word, 'noun')
        result: set = set()
        for g in ('masc', 'fem', 'neut'):
            result |= p.get(g, {}).get(num, {}).get(case, set())
        return result

    def _noun_forms_gender(self, word: str, num: str, case: str, gender: str) -> set:
        forms = self._eee_forms(word, "noun", {
            "Case": _CASE[case], "Number": _NUM[num], "Gender": _GENDER[gender]})
        if forms is not None:
            return forms
        return self._paradigm(word, 'noun').get(gender, {}).get(num, {}).get(case, set())

    def _verb_forms(self, word: str, tense: str, person: str, number: str) -> set:
        base = self._cfg.tense_feats.get(tense)
        if base is None:
            return set()
        forms = self._eee_forms(word, "verb", {
            **base, 'Voice': 'Act', 'Person': _PERSON[person], 'Number': _NUM[number]})
        if forms is not None:
            return forms
        p = self._paradigm(word, 'verb')
        tense_key = self._cfg.path_map.get(tense, tense)
        for voice in ('active', 'passive'):
            forms = p.get(tense_key, {}).get(voice, {}).get('ind', {}).get(number, {}).get(person, set())
            if forms:
                return forms
        return set()

    def _adj_forms(self, word: str, num: str, gender: str, case: str) -> set:
        forms = self._eee_forms(word, "adjective", {
            "Case": _CASE[case], "Number": _NUM[num], "Gender": _GENDER[gender]})
        if forms is not None:
            return forms
        return self._paradigm(word, 'adjective').get('adj', {}).get(num, {}).get(gender, {}).get(case, set())

    @functools.cached_property
    def _adv_slot(self) -> "SlotTemplate | None":
        """The backend's adjective→adverb slot template, resolved once per
        instance — ``get_slot_templates()`` depends only on (language, pos),
        so per-word callers (``adverb_vocab``'s loop) needn't re-fetch it.
        """
        if self._eee is None:
            return None
        slots = self._eee.get_slot_templates(self._cfg.language, "adjective") or []
        return next((s for s in slots if s.tag_type == "ag-paradigm"), None)

    def _adv_forms(self, word: str) -> set:
        """Adverb derived from an adjective (e.g. καλός → καλῶς).

        Goes through the same routing layer as every other slot
        (``get_slot_templates`` + ``inflect_slot``), not a direct backend
        ``.paradigm()`` call — the backend's adverb slot is tagged
        ``tag_type="ag-paradigm"`` (``features=None``) rather than ``"ud"``,
        but ``inflect_slot`` dispatches on that itself, so the caller-side
        shape is identical to any other slot lookup.
        """
        if self._adv_slot is None:
            return set()
        try:
            return self._eee.inflect_slot(word, self._adv_slot, "adjective", language=self._cfg.language)
        except Exception:
            return set()

    def adverb_vocab(self, adjectives: list, word_key: str = "form", meaning_key: str = "meaning") -> "list[dict]":
        """Build a word_drill_form/word_quiz_form-ready vocab list of adjectives'
        derived adverbs (e.g. καλός → καλῶς), via :meth:`_adv_forms`.

        Each output entry is ``{word_key: <adverb>, meaning_key: <original
        meaning>}``; adjectives with no derivable adverb are skipped. When
        ``_adv_forms`` returns more than one variant, the alphabetically
        first is used as the single accepted answer — callers needing every
        variant accepted should check via ``_adv_forms`` directly instead.
        """
        result = []
        for entry in adjectives:
            forms = self._adv_forms(entry[word_key])
            if not forms:
                continue
            result.append({word_key: sorted(forms)[0], meaning_key: entry.get(meaning_key, "")})
        return result

    def _plural_articles(self) -> set:
        """All plural article forms from config (used for pluralia tantum detection)."""
        result: set = set()
        for g_arts in (self._cfg.articles or {}).values():
            for case_forms in g_arts.get('pl', {}).values():
                result.update(case_forms)
        return result

    # --------------------------------------------------------------- data I/O

    @staticmethod
    def _clean_word_row(r) -> "dict | None":
        """Strip Word/Translation from a TSV row; return None if Word is blank."""
        word = str(r.get('Word', '')).strip()
        if not word:
            return None
        return {'Word': word, 'Translation': str(r.get('Translation', '')).strip()}

    def load_slot_drill(
        self,
        path: Any,
        field_features: "dict[str, dict | None]",
        pos: str,
        *,
        backend: "str | None" = None,
    ) -> "list[dict]":
        """Load a Word/Translation TSV and augment each row with inflected forms via UD FEATS.

        ``field_features`` maps output field name → UD feature dict, or ``None``
        to copy the word column unchanged.  Uses ``eee.inflect`` internally —
        no backend-specific slot tags (PAD.2S etc.) needed.

        Example::

            _IMP = {"VerbForm": "Fin", "Tense": "Pres", "Voice": "Act", "Mood": "Imp"}
            VERBS = gu.load_slot_drill(
                Path(__file__).parent / "verbs.tsv",
                {
                    "verb": None,
                    "sg": {**_IMP, "Person": "2", "Number": "Sing"},
                    "pl": {**_IMP, "Person": "2", "Number": "Plur"},
                },
                pos="verb",
            )
        """
        import csv

        lang = self._cfg.language
        result = []
        with open(path, encoding="utf-8") as _f:
            for r in csv.DictReader(_f, delimiter="\t"):
                row = self._clean_word_row(r)
                if row is None:
                    continue
                word = row["Word"]
                item: dict = {"meaning": row["Translation"]}
                for field, feats in field_features.items():
                    if feats is None:
                        item[field] = word
                    else:
                        forms = self._eee.inflect(word, feats, pos, language=lang, backend=backend)
                        item[field] = min(forms, default="")
                result.append(item)
        return result

    def load_data(self, file_upload, _default=None):
        if file_upload.value:
            return self._pd.read_csv(
                io.BytesIO(file_upload.value[0].contents), sep='\t'
            )
        return None

    def get_words(self, table) -> list[dict]:
        if table is None:
            return []
        val = table.value
        if val is None:
            return []
        if isinstance(val, self._pd.DataFrame):
            if val.empty:
                return []
            rows = (self._clean_word_row(r) for _, r in val.iterrows())
            return [r for r in rows if r is not None]
        if not val:
            return []
        rows = (self._clean_word_row(r) for r in val)
        return [r for r in rows if r is not None]

    def make_snapshot(self, form, **kwargs):
        snap = SimpleNamespace(value=list(form.value) if form is not None else [])
        for attr in ('test_word', 'verb_word', 'adj_word', 'adj_mode',
                     'is_pluralia_tantum', 'active_cases'):
            if hasattr(form, attr):
                setattr(snap, attr, getattr(form, attr))
        for k, v in kwargs.items():
            setattr(snap, k, v)
        return snap

    def resolve_word_grammar(self, words, backend, lang="ru"):
        """Augment word dicts with ``grammar_label`` from backend paradigm reverse-lookup.

        For each word with pos ``noun``/``verb``/``adjective``/``pronoun``, finds the
        paradigm slot whose forms contain the word's ``form`` field and formats its UD
        features as a human-readable label.  Words the backend cannot handle get
        ``grammar_label = ""``. All other pos values (particle, adv, prep, conj,
        proper …) are passed through unchanged with ``grammar_label = ""``.

        For ``pos="pronoun"``, slots are additionally filtered by the word's own
        lemma against :data:`_PRON_TYPE` before the tag-matching loop runs --
        pronoun-tags.tsv legitimately has multiple slots sharing the same tag
        across pronoun families (PronType is a per-lemma-family fact layered onto
        an otherwise POS-level tag table), and a naive first-tag-match would
        always resolve to whichever family's row happens to sort first,
        regardless of the word's actual lemma. Lemmas absent from
        :data:`_PRON_TYPE` (i.e. not one of the 10 known pronoun lemmas) fall
        back to the unfiltered slot list, matching the pre-fix behavior rather
        than silently producing no label at all.

        ``lemma`` falls back to ``form`` when absent (flat vocab from
        :meth:`load_vocab_tsv`) — see the "form vs. lemma" note in
        ``docs/api-patterns.md``.
        """
        _slots_by_pos: dict = {}
        result = []
        for w in words:
            w = dict(w)
            pos = w.get("pos", "")
            eee_pos = LEXICON_TAG_POS_ALIASES.get(pos, pos)
            w["grammar_label"] = ""
            if pos in LEXICON_TAG_POS and backend is not None:
                form = w.get("form", "")
                lemma = _lemma_of(w, form)
                try:
                    paradigm = backend.paradigm(lemma, eee_pos)
                    if eee_pos not in _slots_by_pos:
                        _slots_by_pos[eee_pos] = backend.get_slot_templates("grc", eee_pos, lang) or []
                    slots = _slots_by_pos[eee_pos]
                    if eee_pos == "pronoun":
                        # Unnormalized dict lookup on Greek text -- if a
                        # vocab lemma ever arrives in a different Unicode
                        # normalization form than _PRON_TYPE's own
                        # literals, this silently misses and falls back
                        # to unfiltered (pre-fix) behavior rather than
                        # erroring. Mirrors backend.paradigm(lemma, ...)
                        # just above, which has the same unnormalized-
                        # lookup shape -- not a new risk class introduced
                        # here, flagged in code review as worth knowing
                        # about rather than a confirmed live bug.
                        want_prontype = _PRON_TYPE.get(lemma)
                        if want_prontype is not None:
                            slots = [s for s in slots if (s.features or {}).get("PronType") == want_prontype]
                    for slot in slots:
                        if form in paradigm.get(slot.tag, set()):
                            feats = slot.features or {}
                            ud = "|".join(f"{k}={v}" for k, v in feats.items())
                            w["grammar_label"] = fmt_ud_feats(ud, lang)
                            break
                except Exception:
                    pass
            result.append(w)
        return result

    # ------------------------------------------------------------------ nouns

    def noun_drill_meta(self, word: str) -> SimpleNamespace:
        """``is_pluralia_tantum`` + ``active_cases`` for one noun lemma
        (article-prefixed, e.g. "ὁ λόγος") — the metadata
        :meth:`noun_paradigm_drill_form` needs, without building any
        widgets. :meth:`create_noun_test_ui` attaches the same two fields
        to the form it returns.
        """
        parts = word.split()
        nw = parts[1].strip() if len(parts) > 1 else word.strip()
        na = parts[0].strip() if len(parts) > 1 else None
        noun_cells = self._cfg.noun_cells
        pl_cells = [c for c in noun_cells if c[0] == 'pl']
        _sg_nom_forms = self._noun_forms(nw, 'sg', 'nom')
        is_pt = (
            (na is not None and na in self._plural_articles()) or
            not bool(_sg_nom_forms)
        )
        active_cases = (
            pl_cells if is_pt else
            # noun_cells[0] is always ('sg', 'nom') — reuse _sg_nom_forms
            # instead of re-querying it (it's truthy here, since is_pt is False)
            [noun_cells[0]] + [c for c in noun_cells[1:] if bool(self._noun_forms(nw, c[0], c[1]))] or noun_cells
        )
        return SimpleNamespace(is_pluralia_tantum=is_pt, active_cases=active_cases)

    def _slot_label_index(self, pos: str, lang: str) -> dict:
        """``{frozenset(features): label}`` for every backend-resolved slot
        template of *pos* in *lang* — shared by :meth:`noun_slot_labels` and
        :meth:`_adj_slot_names`. ``label == tag`` means the backend echoed
        its internal tag string back unresolved (no real localized text
        available for this slot, or at all -- e.g. ancient-greek-backend-eee's
        get_slot_templates() never resolves terms_lang, by its own
        docstring) -- treated the same as "not found" rather than surfacing
        a raw tag like ".NSM" to a student.
        """
        slots = self._eee.get_slot_templates(self._cfg.language, pos, lang) if self._eee else None
        return {
            frozenset(s.features.items()): s.label
            for s in (slots or []) if s.features and s.label != s.tag
        }

    def noun_slot_labels(self, active_cases: list, lang: str = "en") -> list:
        """Labels for a noun paradigm-drill's slots — one per ``(number,
        case)`` pair in ``active_cases`` (see :meth:`noun_drill_meta`),
        e.g. "Nom. Sg.:", in the same slot order ``check_noun_slot`` indexes.

        ``lang`` (``"en"``/``"ru"``/``"el"``) selects the label language via
        ``get_slot_templates(..., terms_lang=lang)`` — the bundled
        ``eee_project.data.labels/noun-{lang}.tsv`` backs this the same way
        it backs any other slot-template consumer (never read directly here;
        always through the routing layer, per this project's own tagging
        rule). Falls back to the English quiz-label dicts for any (number,
        case) pair the template doesn't cover (e.g. no ``eee_module``).
        """
        by_feats = self._slot_label_index("noun", lang)
        labels = []
        for n, c in active_cases:
            label = by_feats.get(frozenset({"Case": _CASE.get(c, c), "Number": _NUM.get(n, n)}.items()))
            if label is None:
                label = f"{_QUIZ_CASE_LABEL.get(c, c)} {_QUIZ_NUM_LABEL.get(n, n)}"
            labels.append(f"{label}:")
        return labels

    def noun_indef_cells(self, active_cases: list) -> list:
        """The singular-only subset of *active_cases* indefinite-article
        slots apply to — indefinite articles don't inflect for plural.

        Returns ``[]`` when ``config.indef_articles`` is unset (e.g.
        Ancient Greek), so callers (:meth:`create_noun_test_ui`,
        :meth:`check_noun_test`, :meth:`check_noun_slot`, and notebooks
        building an ``indefinite=True`` label list) can call this
        unconditionally without checking the config themselves first.
        """
        return [c for c in active_cases if c[0] == 'sg'] if self._cfg.indef_articles else []

    def create_noun_test_ui(self, words_list, mode='simple'):
        mo = self._mo
        word = translation = noun_form = None
        if words_list and words_list[0]:
            entry = words_list[0]
            word = entry['Word'] if isinstance(entry, dict) else entry
            translation = entry.get('Translation', '') if isinstance(entry, dict) else ''
            meta = self.noun_drill_meta(word)
            is_pt, active_cases = meta.is_pluralia_tantum, meta.active_cases
            indef_cells = self.noun_indef_cells(active_cases)
            if mode == 'simple':
                labels = self.noun_slot_labels(active_cases)
            else:
                labels = (
                    [f"Def. {l}" for l in self.noun_slot_labels(active_cases)] +
                    [f"Ind. {l}" for l in self.noun_slot_labels(indef_cells)]
                )
            noun_form = mo.ui.array([mo.ui.text(label=l) for l in labels])
            noun_form.test_word = word
            noun_form.is_pluralia_tantum = is_pt
            noun_form.active_cases = active_cases
        return word, translation, noun_form

    def _noun_gender_from_article(self, parts: list) -> "list | None":
        """Detect gender from a noun lemma's leading article (e.g. ["ὁ", "ἀγρός"] -> ["masc"]).

        Shared by check_noun_test and check_noun_slot — the ancient-greek
        backend returns forms for every gender requested rather than only
        the word's actual gender, so detecting from the article avoids
        _noun_forms_gender's own gender fan-out returning a false-positive
        union of genders (bug-719).
        """
        arts = self._cfg.articles
        if not arts or len(parts) <= 1:
            return None
        nom_art = parts[0].strip()
        from_art = [g for g in ('masc', 'fem', 'neut')
                    if nom_art in arts.get(g, {}).get('sg', {}).get('nom', set())]
        return from_art or None

    def _noun_genders_at(self, nw: str, num: str, case: str, detected: "list | None") -> list:
        """Resolve genders for one noun-form slot: ``detected`` if known,
        else every gender that has any form there (per _noun_forms_gender's
        own imperfect fan-out — see _noun_gender_from_article).
        """
        if detected is not None:
            return detected
        return [g for g in ('masc', 'fem', 'neut') if self._noun_forms_gender(nw, num, case, g)]

    def check_noun_test(self, noun, noun_form, mode='simple', *, article: bool = False, indefinite: bool = False):
        """Check noun paradigm form against backend.

        Returns ``(ok, feedback_html)`` where ``feedback_html`` is a
        ``'<br>'``-joined string of error messages (empty when correct).
        ``article=True`` requires the definite article in each field (Ancient Greek drills).
        ``article=False`` (default): articles are validated if the user types one,
        but not required — a bare noun form is accepted.

        ``indefinite=True`` (``mode='simple'`` only) additionally checks
        extra indefinite-article slots appended after the definite ones, one
        per singular case (indefinite articles don't inflect for plural) —
        pass ``noun_form.value`` with that many extra entries, e.g. built via
        ``noun_slot_labels(active_cases) + noun_slot_labels(noun_indef_cells(active_cases))``
        (see :meth:`check_noun_slot`'s matching ``indefinite`` param for the
        Enter-driven per-slot equivalent). No-ops when ``config.indef_articles``
        is unset (e.g. Ancient Greek). ``mode='full'`` already tests both
        halves unconditionally, independent of this param — see below.
        """
        if not noun or noun_form is None or not noun_form.value:
            return False, ""
        if hasattr(noun_form, 'test_word') and noun_form.test_word != noun:
            return False, ""
        parts = noun.split()
        nw = parts[1].strip() if len(parts) > 1 else noun.strip()
        is_pt = getattr(noun_form, 'is_pluralia_tantum', False)
        ac = getattr(noun_form, 'active_cases', None)
        noun_cells = self._cfg.noun_cells
        if not isinstance(ac, list):
            pl_cells = [list(c) for c in noun_cells if c[0] == 'pl']
            ac = pl_cells if is_pt else [list(c) for c in noun_cells]
        arts = self._cfg.articles
        indef_arts = self._cfg.indef_articles
        _detected_genders = self._noun_gender_from_article(parts)

        def _genders_at(num, case):
            return self._noun_genders_at(nw, num, case, _detected_genders)

        def _chk(val, num, case, art_table=None, require_art=True):
            if not val:
                return False, []
            ws = val.split()
            uw, ua = ws[-1].strip(), (ws[0].strip() if len(ws) > 1 else None)
            correct = self._noun_forms(nw, num, case)
            correct_arts: set = set()
            if art_table is not None:
                for g in _genders_at(num, case):
                    correct_arts.update(art_table.get(g, {}).get(num, {}).get(case, set()))
            _n = _QUIZ_NUM_LABEL.get(num, num)
            _c = _QUIZ_CASE_LABEL.get(case, case)
            errs = []
            if art_table is not None:
                if ua is None:
                    if require_art:
                        errs.append(f'❌ [{_c} {_n}]: article missing, must be **{" / ".join(sorted(correct_arts))}**')
                elif not self._ci(ua, correct_arts):
                    errs.append(f'❌ [{_c} {_n}]: article **"{ua}"**, must be **{" / ".join(sorted(correct_arts))}**')
            if not self._ci(uw, correct):
                errs.append(f'❌ [{_c} {_n}]: noun **"{uw}"**, must be **{" / ".join(sorted(correct)) if correct else "?"}**')
            return not errs, errs

        def _collect(results):
            ok = all(r[0] for r in results)
            errs = [e for r in results for e in r[1]]
            return ok, '<br>'.join(errs)

        # 'full' mode is 'simple' with article/indefinite both forced True —
        # it predates those two params and always tested both halves
        # unconditionally, so it keeps its own hardcoded require_art=True
        # rather than reading `article`, and never reads `indefinite` at all.
        # noun_indef_cells already no-ops to [] without config.indef_articles,
        # so the only thing left to gate on here is 'simple' mode's own
        # indefinite opt-in — an empty indef_cells falls through harmlessly
        # (zip against it yields no pairs), no separate early-return needed.
        if mode == 'simple':
            def_res = [_chk(v, c[0], c[1], arts, require_art=article)
                       for v, c in zip(noun_form.value, ac)]
            indef_cells = self.noun_indef_cells(ac) if indefinite else []
        else:
            def_res = [_chk(v, c[0], c[1], arts, require_art=True)
                       for v, c in zip(noun_form.value, ac)]
            indef_cells = self.noun_indef_cells(ac)
        indef_res = [_chk(v, c[0], c[1], indef_arts)
                     for v, c in zip(noun_form.value[len(ac):], indef_cells)]
        return _collect(def_res + indef_res)

    def _noun_slot_check(self, noun, num, case, value, art_table, require_art) -> bool:
        """Shared form+article check for one (number, case) pair against one
        article table — the boolean-only sibling of check_noun_test's _chk
        (which additionally builds error messages, so isn't reused directly).
        Used by check_noun_slot for both its definite and indefinite slots.
        """
        parts = noun.split()
        nw = parts[1].strip() if len(parts) > 1 else noun.strip()
        val = (value or '').strip()
        if not val:
            return False
        ws = val.split()
        uw, ua = ws[-1].strip(), (ws[0].strip() if len(ws) > 1 else None)
        if not self._ci(uw, self._noun_forms(nw, num, case)):
            return False
        if not require_art or not art_table:
            return True
        if ua is None:
            return False
        detected = self._noun_gender_from_article(parts)
        genders = self._noun_genders_at(nw, num, case, detected)
        correct_arts = set()
        for g in genders:
            correct_arts.update(art_table.get(g, {}).get(num, {}).get(case, set()))
        return self._ci(ua, correct_arts)

    def check_noun_slot(self, noun, slot_index, value, *, article=False, active_cases=None, indefinite=False):
        """Check a single noun-form slot (index into *active_cases* or config.noun_cells).

        Same comparison rules as ``check_noun_test``'s per-slot logic (form +
        required article), for one slot only — for incremental per-field
        validation (e.g. on Enter) instead of a full-form check. Pass the same
        ``active_cases`` the form was built with (e.g. pluralia tantum uses a
        plural-only subset) so slot indices line up.

        ``indefinite=True`` extends the valid slot range past ``active_cases``:
        indices ``len(active_cases)`` onward index into its singular-only
        subset (indefinite articles don't inflect for plural), checked against
        ``config.indef_articles`` instead of ``config.articles`` — an
        indefinite slot always requires its article (that's the whole point
        of the slot), independent of ``article``, which only controls the
        definite slots. A ``False`` (or missing ``config.indef_articles``,
        e.g. Ancient Greek) leaves the valid range unchanged.
        """
        cells = active_cases if active_cases is not None else self._cfg.noun_cells
        if 0 <= slot_index < len(cells):
            num, case = cells[slot_index]
            return self._noun_slot_check(noun, num, case, value, self._cfg.articles, article)
        if indefinite:
            indef_cells = self.noun_indef_cells(cells)
            j = slot_index - len(cells)
            if 0 <= j < len(indef_cells):
                num, case = indef_cells[j]
                return self._noun_slot_check(noun, num, case, value, self._cfg.indef_articles, True)
        return False

    # ------------------------------------------------------------------ verbs

    def verb_slot_labels(self) -> list:
        """Labels for the verb paradigm-drill's slots (``config.verb_labels``
        with trailing colons), in the same slot order ``check_verb_slot``
        indexes — what :meth:`create_verb_test_ui` renders.
        """
        return [f"{lbl}:" for lbl in self._cfg.verb_labels]

    def create_verb_test_ui(self, title, words, words4test_val, current_verb):
        mo = self._mo
        form = None
        md_view = mo.md(f'**The word list for {title} is empty.**')
        if current_verb:
            word = current_verb['Word']
            translation = current_verb['Translation']
            form = mo.ui.array([mo.ui.text(label=l) for l in self.verb_slot_labels()])
            form.verb_word = word
            if words4test_val:
                md_view = mo.md(f"""
### {title}
(words: {len(words4test_val)}/{len(words)})
Translation: **{translation}**
{form}
""")
        return form, md_view

    def _verb_slot_ok(self, verb_base, tense, per, n, value):
        """Check one verb-form slot; returns (ok, cv, correct, pref).

        ``cv`` is the prefix-stripped value (``None`` if a required prefix
        was missing entirely, distinct from an empty string after stripping);
        ``correct`` is the correct-forms set; ``pref`` is the tense's
        required prefix (empty if none). Shared by check_verb_test (full-form,
        builds formatted errors from these parts) and check_verb_slot
        (single-slot boolean check).
        """
        pref = self._cfg.verb_prefix.get(tense, '')
        uv = (value or '').strip()
        if not uv:
            return False, None, set(), pref
        cv = uv
        if pref:
            if uv.lower().startswith(pref):
                cv = uv[len(pref):].strip()
            else:
                return False, None, set(), pref
        correct = self._verb_forms(verb_base, tense, per, n)
        ok = bool(correct) and self._ci(cv, correct)
        return ok, cv, correct, pref

    def check_verb_test(self, verb_base, form_array, tense):
        """Check verb paradigm form against backend.

        Returns ``(ok, feedback_html)`` where ``feedback_html`` is a
        ``'<br>'``-joined string of error messages (empty when correct).
        """
        if form_array is None or not form_array.value:
            return False, ""
        if hasattr(form_array, 'verb_word') and form_array.verb_word != verb_base:
            return False, ""
        if tense not in self._cfg.tense_feats:
            return False, f"Unknown tense '{tense}'"
        ok, errs = True, []
        for i, ((n, per), lbl) in enumerate(zip(self._cfg.verb_slots, self._cfg.verb_labels)):
            uv = form_array.value[i].strip()
            if not uv:
                ok = False
                continue
            slot_ok, cv, correct, pref = self._verb_slot_ok(verb_base, tense, per, n, uv)
            if not slot_ok:
                ok = False
                if cv is None and pref:
                    errs.append(f'❌ [{lbl}]: Write with **"{pref}"**')
                else:
                    exp = '/'.join(correct) if correct else 'unknown'
                    if pref:
                        exp = f"{pref} {exp}"
                    errs.append(f'❌ [{lbl}]: entered **"{uv}"**, must be **{exp}**')
        return ok, '<br>'.join(errs)

    def check_verb_slot(self, verb_base, tense, slot_index, value):
        """Check a single verb-form slot (index into config.verb_slots).

        Same comparison rules as ``check_verb_test``'s per-slot logic (prefix +
        form), for one slot only — for incremental per-field validation (e.g.
        on Enter) instead of a full-form check.
        """
        if tense not in self._cfg.tense_feats or not (0 <= slot_index < len(self._cfg.verb_slots)):
            return False
        n, per = self._cfg.verb_slots[slot_index]
        ok, _, _, _ = self._verb_slot_ok(verb_base, tense, per, n, value)
        return ok

    # --------------------------------------------------------------- adjectives

    def create_adjective_test_ui(self, words, words4test_val, current_adj, mode='simple'):
        mo = self._mo
        form = None
        md_view = mo.md('**The word list for adjective test is empty.**')
        if current_adj:
            word = current_adj['Word']
            translation = current_adj['Translation']
            labels = self.adjective_slot_labels(mode)
            form = mo.ui.array([mo.ui.text(label=l) for l in labels])
            form.adj_word = word
            form.adj_mode = mode
            if words4test_val:
                md_view = mo.md(f"""
### Test: Adjective Declension ({len(words4test_val)}/{len(words)})
Translation: **{translation}**
{form}
""")
        return form, md_view

    def _adj_slot_list(self, mode: str) -> list:
        """(gender, number, case) tuples for check_adjective_test/check_adjective_slot/
        adjective_slot_labels, shared so the three stay in sync. ``'simple'``
        tests nominative only (6 slots: 3 genders x 2 numbers); anything
        else tests every case in ``config.adj_cases`` (masc/fem/neut x sg/pl
        x case).
        """
        if mode == 'simple':
            return ([(g, 'sg', 'nom') for g in ('masc', 'fem', 'neut')] +
                    [(g, 'pl', 'nom') for g in ('masc', 'fem', 'neut')])
        return [(g, n, c) for n in ('sg', 'pl')
                for g in ('masc', 'fem', 'neut') for c in self._cfg.adj_cases]

    def _adj_slot_names(self, mode: str, lang: str = "en") -> list:
        """Human-readable name per ``_adj_slot_list`` slot (no trailing
        colon), e.g. "Nom. Sg. m." — the single source behind
        check_adjective_test's error labels and adjective_slot_labels.

        ``lang`` (``"en"``/``"ru"``/``"el"``) selects the label language via
        ``get_slot_templates(..., terms_lang=lang)`` — see
        :meth:`noun_slot_labels` for the mechanism (same routing layer,
        backed by ``eee_project.data.labels/adj-{lang}.tsv`` here instead).
        Falls back to the English quiz-label dicts for any slot the
        template doesn't cover.
        """
        cm = {c: c.title() for c in self._cfg.adj_cases}
        fk = self._adj_slot_list(mode)
        by_feats = self._slot_label_index("adjective", lang)
        names = []
        for g, n, c in fk:
            label = by_feats.get(frozenset({"Case": _CASE.get(c, c), "Number": _NUM.get(n, n), "Gender": _GENDER.get(g, g)}.items()))
            if label is None:
                label = (f"{_QUIZ_ADJ_GENDER[g]} {_QUIZ_ADJ_NUM[n]}" if mode == 'simple'
                          else f"{_QUIZ_ADJ_GENDER[g]} {_QUIZ_ADJ_NUM[n]} {cm.get(c, c)}")
            names.append(label)
        return names

    def _adj_slot_ok(self, adj_base, g, n, c, value) -> tuple:
        """Check one adjective-form slot; returns (ok, correct_forms).

        Falls back to the base form itself when no backend data exists.
        Shared by check_adjective_test (needs ``correct_forms`` for its
        error message) and check_adjective_slot (boolean only) — mirrors
        ``_verb_slot_ok``.
        """
        correct = self._adj_forms(adj_base, n, g, c) or {adj_base}
        return self._ci(value, correct), correct

    def check_adjective_test(self, adj_base, form_array, mode='simple'):
        """Check adjective paradigm form against backend.

        Returns ``(ok, feedback_html)`` where ``feedback_html`` is a
        ``'<br>'``-joined string of error messages (empty when correct).
        ``mode`` selects the slot list (``'simple'`` = nom sg/pl all genders;
        see ``_adj_slot_list``).
        """
        if form_array is None or not form_array.value:
            return False, ""
        if hasattr(form_array, 'adj_word') and form_array.adj_word != adj_base:
            return False, ""
        if hasattr(form_array, 'adj_mode'):
            mode = form_array.adj_mode
        fk = self._adj_slot_list(mode)
        fl = self._adj_slot_names(mode)
        ok, has, errs = True, False, []
        for i, ((g, n, c), label) in enumerate(zip(fk, fl)):
            uv = form_array.value[i].strip()
            if not uv:
                ok = False
                continue
            has = True
            slot_ok, correct = self._adj_slot_ok(adj_base, g, n, c, uv)
            if not slot_ok:
                ok = False
                errs.append(f'❌ [{label}]: entered **"{uv}"**, must be **{"/".join(sorted(correct))}**')
        if not has:
            return False, '❌ Please fill in at least one gender form'
        return ok, '<br>'.join(errs)

    def check_adjective_slot(self, adj_base, mode, slot_index, value):
        """Check a single adjective-form slot (index into the same slot list
        check_adjective_test uses for the given mode). Same comparison rule
        (fall back to the base form itself when no backend data exists),
        for one slot only — for incremental per-field validation (e.g. on
        Enter) instead of a full-form check.
        """
        fk = self._adj_slot_list(mode)
        if not (0 <= slot_index < len(fk)):
            return False
        g, n, c = fk[slot_index]
        ok, _ = self._adj_slot_ok(adj_base, g, n, c, (value or '').strip())
        return ok

    def adjective_slot_labels(self, mode: str = 'simple', lang: str = "en") -> list:
        """Labels for the adjective paradigm-drill's slots, matching the
        same order as check_adjective_slot's slot list for the same mode.

        ``lang`` (``"en"``/``"ru"``/``"el"``) selects the label language —
        see :meth:`_adj_slot_names`.
        """
        return [f"{name}:" for name in self._adj_slot_names(mode, lang)]

    # --------------------------------------------------------------- item drills

    def make_item_drill_rows(
        self,
        items: "list[dict]",
        fields: "list[str]",
        *,
        meaning_key: str = "meaning",
        placeholders: "list[str] | None" = None,
        use_diacritics: bool = False,
    ) -> "tuple[list[list], list]":
        """Create text inputs for a multi-row slot drill.

        Args:
            items:       List of dicts, each representing one drill item.
            fields:      Keys in each item dict whose values are the expected
                         answers (one text input per field).
            meaning_key: Key in each item dict used as the row prompt label.
            placeholders: Optional placeholder strings, one per field.

        Returns ``(inputs_2d, rows)`` where ``inputs_2d[i][j]`` is the
        ``mo.ui.text`` for item *i* field *j*, and ``rows`` is a list of
        ``mo.hstack`` row widgets ready to spread into a ``mo.vstack``.

        Example cell (palaestra-style imperatives drill)::

            inputs_2d, _rows = gu.make_item_drill_rows(
                VERBS, ["verb", "sg", "pl"],
                meaning_key="meaning",
                placeholders=["verb…", "sg…", "pl…"],
            )
            mo.vstack([mo.md("## Exercise"), *_rows, submit_btn])
        """
        mo = self._mo
        phs = ((placeholders or []) + ["…"] * len(fields))[:len(fields)]
        def _input(ph):
            if use_diacritics:
                return diacritics_text(mo, placeholder=ph)
            return mo.ui.text(placeholder=ph)
        inputs_2d = [
            [_input(phs[j]) for j in range(len(fields))]
            for _ in items
        ]
        rows = [
            mo.hstack(
                [mo.md(f"**{item[meaning_key]}**")] + inputs_2d[i],
                justify="start",
            )
            for i, item in enumerate(items)
        ]
        return inputs_2d, rows

    def check_item_drill(
        self,
        items: "list[dict]",
        inputs_2d: "list[list]",
        fields: "list[str]",
        *,
        meaning_key: str = "meaning",
        field_labels: "list[str] | None" = None,
        strict: "bool | None" = None,
    ) -> list:
        """Check student answers for a drill created by :meth:`make_item_drill_rows`.

        Args:
            items:        Same list passed to :meth:`make_item_drill_rows`.
            inputs_2d:    Return value from :meth:`make_item_drill_rows`.
            fields:       Same list passed to :meth:`make_item_drill_rows`.
            meaning_key:  Key used for the item label in feedback.
            field_labels: Human-readable label for each field (defaults to field key).
            strict:       ``True`` requires exact diacritics; ``False`` ignores
                          them; ``None`` (default) uses ``config.compare_diacritics``.

        Returns a list of ``mo.md(...)`` feedback elements — one per item that
        has at least one non-empty input.  Feed the list to ``mo.vstack``.

        Example result cell::

            _fb = gu.check_item_drill(
                VERBS, verb_inputs_v, ["verb", "sg", "pl"],
                field_labels=["verb", "sg.", "pl."],
            ) if submit_btn.value else []
            mo.vstack(_fb) if _fb else mo.md("")
        """
        _strict = self._cfg.compare_diacritics if strict is None else strict
        mo = self._mo
        lbls = ((field_labels or []) + list(fields))[:len(fields)]
        feedback = []
        for i, item in enumerate(items):
            parts = []
            for j, field in enumerate(fields):
                val = inputs_2d[i][j].value.strip()
                if not val:
                    continue
                expected = item.get(field, "")
                ok = greek_compare(val, expected, diacritics=_strict)
                lbl = lbls[j]
                parts.append(
                    f"{'✓' if ok else '✗'} {lbl} **{val}**" +
                    (f" ← *{expected}*" if not ok else "")
                )
            if parts:
                feedback.append(mo.md(f"*{item[meaning_key]}*: " + " · ".join(parts)))
        return feedback

    def _feedback_md(self, mo: Any, ok: bool, meaning: str, form: str) -> Any:
        """Return a colored ✓/✗ inline feedback span."""
        color = "#2d9e2d" if ok else "#d32f2f"
        mark = "✓" if ok else "✗"
        return mo.md(f'<span style="color:{color};font-weight:bold">{mark} {meaning} → {form}</span>')

    def _quiz_result_span(self, mo: Any, fb_ans: "str | None", correct: "str | None", lang: str) -> Any:
        """Colored ✓/✗ feedback span revealing the correct answer on a wrong
        pick, or an empty element before any answer is given.

        Shared by :meth:`stanza_match_form` and :meth:`translation_presence_form`,
        whose free-text/да-нет answer options can't reuse :meth:`_feedback_md`'s
        fixed "meaning → form" template.
        """
        if fb_ans is None:
            return mo.md("")
        ok = fb_ans == correct
        color = "#2d9e2d" if ok else "#d32f2f"
        mark = _QUIZ_RIGHT.get(lang, "✓") if ok else f"{_QUIZ_INCORRECT.get(lang, '✗')} {correct}"
        return mo.md(f'<span style="color:{color};font-weight:bold">{mark}</span>')

    def _render_table_or_error(self, build_paradigm_table, word: dict, lang: str) -> tuple:
        """Call build_paradigm_table(word, lang=lang); returns (html_or_None, error_or_None).

        Shared by word_quiz_feedback and word_quiz_form, which each decide
        differently what to render when the table is empty/None (no error).
        """
        try:
            html = build_paradigm_table(word, lang=lang)
            return html, None
        except Exception as e:
            return None, str(e)

    def _make_nav_buttons(self, *, done: bool = False, history_len: int = 0, lang: str = "ru") -> tuple:
        """Return ``(next_btn, prev_btn)`` for word-drill / word-quiz exercises."""
        mo = self._mo
        _next_lbl = _NAV_AGAIN.get(lang, "Again") if done else _NAV_NEXT.get(lang, "Next")
        return (
            mo.ui.button(label=_next_lbl, on_click=_INC),
            mo.ui.button(label=_NAV_PREV.get(lang, "Prev"), on_click=_INC, disabled=history_len == 0),
        )

    def _nav_row(self, *buttons: Any, justify: str = "start") -> Any:
        """``mo.hstack`` of *buttons*, dropping any that are ``None`` (e.g. an
        optional ``renew_btn`` a caller didn't pass). Shared by
        :meth:`word_quiz_form`, :meth:`stanza_match_form`, and
        :meth:`translation_presence_form`."""
        return self._mo.hstack([b for b in buttons if b is not None], justify=justify)

    def make_renew_button(self) -> Any:
        """``↺`` button whose value counts clicks. Notebooks put it in its own
        cell and read ``.value`` elsewhere to force a fresh session sample."""
        return self._mo.ui.button(label="↺ Новый набор", on_click=_INC)

    def ictus_toggle_panel(self, show_ictus: Any, show_homer: Any, eee_note: str, *,
                            ictus_color: str, ictus_color_name: str) -> Any:
        """SHOW_ICTUS/SHOW_HOMER toggle row + EEE-engine note accordion.

        *show_ictus*/*show_homer* are the caller's already-built
        ``mo.ui.switch`` elements; *eee_note* is the already-resolved note
        text (loaded from ``eee_note.md`` or inline, caller's choice).
        *ictus_color*/*ictus_color_name* are the CSS color and its Russian
        name used in the ictus-highlighting sentence -- lessons vary this
        (e.g. red vs. green) to match their own ``ictus.html``.
        """
        return self._mo.vstack(
            [
                self._mo.hstack(
                    [show_ictus, self._mo.md(
                        f"Икты (ударные слоги) каждой стопы выделены "
                        f"<b style='color:{ictus_color}'>{ictus_color_name}</b>."
                    )],
                    justify="start", align="center", gap=1.5,
                ),
                self._mo.hstack(
                    [show_homer, self._mo.md(
                        "Слова из гомеровского лексикона, для которых движок EEE строит "
                        "таблицы словоформ по разным периодам греческого языка."
                    )],
                    justify="start", align="center", gap=1.5,
                ),
                self._mo.accordion({"О морфологическом движке EEE": eee_note}),
            ],
            align="stretch", gap=0.5,
        )

    def render_gloss_panel(self, quiz_words_raw: list, selected_word: str,
                            build_lexicon_tabs: Any) -> Any:
        """Word-click gloss panel: resolve *selected_word* against
        *quiz_words_raw*, show its translation/grammar label, and (if any
        curated lexicon attests the exact form) a per-lexicon paradigm-table
        caption via *build_lexicon_tabs*."""
        w = resolve_clicked_word(quiz_words_raw, selected_word)
        if w is None:
            return self._mo.md(
                "*Выберите слово в тексте, чтобы увидеть перевод и формы "
                "слов из гомеровскго лексикона…*"
            )
        w2 = dict(w)
        add_labels([w2])
        gloss = f"**{w2.get('form', selected_word)}** — {w2['_label']}"
        grammar = w2.get("grammar_label", "")
        if grammar:
            gloss += f"  \n_{grammar}_"
        tables = build_lexicon_tabs(w2) or ""
        if not tables:
            return self._mo.md(gloss)
        caption = self._mo.md(
            "*Формы слова по эпохам — только простейшее морфологическое "
            "соответствие по леммам, смысл может меняться*"
        )
        return self._mo.vstack([self._mo.md(gloss), caption, self._mo.Html(tables)])

    @staticmethod
    def reset_quiz_state(renew_btn: Any, set_cv, set_remaining, set_score,
                          set_history, set_future, set_restore_entry) -> None:
        """Reset one exercise's cv/remaining/score/history/future/
        restore_entry state to a fresh session's starting values.

        *renew_btn* is only read (not otherwise used) so marimo's reactive
        graph re-runs the caller's cell when the button is clicked -- same
        role ``_ = renew_btn.value`` played inline before this was factored
        out. Shared by the session-sampling cells in
        :meth:`word_quiz_form`, :meth:`stanza_match_form`, and
        :meth:`translation_presence_form`'s notebook wiring.
        """
        _ = renew_btn.value
        set_cv(None)
        set_remaining(None)
        set_score({"correct": 0, "total": 0})
        set_history([])
        set_future([])
        set_restore_entry(None)

    def _make_future_entry(self, cv: dict, restore_entry: "dict | None") -> dict:
        """Build the future-stack entry for the word currently on screen."""
        return {
            "word": cv,
            "answer": restore_entry["answer"] if restore_entry else None,
            "correct": restore_entry["correct"] if restore_entry else None,
        }

    def sample_session_items(self, items: list, n: int = 10) -> list:
        """Randomly pick up to *n* items from *items* for one exercise session.

        Serving a lesson's full vocab/stanza/item pool every session — some
        lessons run past 100 words — makes a session either too long to
        finish or, worse, easy enough to game by memorizing raw position
        rather than the material. Returns *items* unchanged (not padded,
        never errors) when there are already *n* or fewer.

        Call this on the pool a notebook cell builds (e.g. ``QUIZ_WORDS`` or
        a lesson's stanza list) *before* handing it to a ``*_widgets``/
        ``*_form`` pair — :meth:`_shuffle_start` still shuffles whatever it's
        given, it just no longer sees the full pool.
        """
        return _random.sample(items, min(n, len(items)))

    def _shuffle_start(self, vocab: list, set_cv, set_remaining) -> None:
        """Shuffle *vocab* and set the first word as current with the rest as remaining."""
        _shuf = _random.sample(vocab, len(vocab))
        set_cv(_shuf[0])
        set_remaining(_shuf[1:])

    def _restart_quiz(self, vocab: list, set_cv, set_remaining,
                       set_score, set_history, set_future, set_restore) -> None:
        """Reset all state for starting over after 'done' (word_drill_form/word_quiz_form)."""
        self._shuffle_start(vocab, set_cv, set_remaining)
        set_score({"correct": 0, "total": 0})
        set_history([])
        set_future([])
        set_restore(None)

    def save_entry(self, entered: dict, cv: "dict | None", form, *, word_key: str = "form") -> dict:
        """Merge the current paradigm-form values into a per-word
        entered-values dict, keyed by ``cv[word_key]`` — a no-op (returns
        ``entered`` unchanged) when ``cv`` is ``None``.

        For notebooks built directly on ``make_paradigm_form`` rather than
        ``word_quiz_form``/``word_drill_form`` (a full multi-field paradigm
        per word, not one question at a time): call this from the
        correct-answer and prev/next handlers to persist the just-typed
        values before moving on, so ``make_paradigm_form(values=...)`` can
        restore them if the student navigates back. ``word_key`` names the
        current word's identifying field in the caller's vocab dict
        (``"form"`` for ``load_vocab_tsv``'s schema, e.g. ``word_key="Word"``
        for others) — pass ``cv=None`` when there's no current word.
        """
        if cv is None:
            return entered
        return {**entered, cv[word_key]: list(form.widget.values)}

    def make_paradigm_drill_state(self, initial_words: list) -> tuple:
        """Create the 10 ``mo.state()`` pairs a paradigm-drill exercise
        needs, as a flat 20-tuple in the same order
        :meth:`_pack_paradigm_state` takes them positionally — unpack
        directly in the notebook cell that owns these names::

            (words, set_words, hist, set_hist, msg, set_msg, cap, set_cap,
             entered, set_entered, sub_cnt, set_sub_cnt, prev_cnt, set_prev_cnt,
             nxt_cnt, set_nxt_cnt, entercnt, set_entercnt, restart_cnt,
             set_restart_cnt) = gu.make_paradigm_drill_state(initial_words)

        Safe to call directly from a notebook cell (unlike
        :meth:`_pack_paradigm_state`, which is internal-only) — the names
        above are literal assignment targets in the calling cell's own
        source, so marimo's static reactivity tracking sees them exactly
        as if the cell had called ``mo.state()`` ten times itself; nothing
        crosses a cell boundary through a dict/attribute lookup.

        ``initial_words`` seeds the word queue (e.g. already shuffled via
        ``random.sample`` for a randomized drill order); everything else
        starts empty/zero/``None``, matching what
        :meth:`reset_paradigm_drill_state` resets back to.
        """
        mo = self._mo
        words, set_words = mo.state(list(initial_words))
        hist, set_hist = mo.state([])
        msg, set_msg = mo.state("")
        cap, set_cap = mo.state(None)
        entered, set_entered = mo.state({})
        sub_cnt, set_sub_cnt = mo.state(0)
        prev_cnt, set_prev_cnt = mo.state(0)
        nxt_cnt, set_nxt_cnt = mo.state(0)
        entercnt, set_entercnt = mo.state(0)
        restart_cnt, set_restart_cnt = mo.state(0)
        return (
            words, set_words, hist, set_hist, msg, set_msg, cap, set_cap,
            entered, set_entered, sub_cnt, set_sub_cnt, prev_cnt, set_prev_cnt,
            nxt_cnt, set_nxt_cnt, entercnt, set_entercnt, restart_cnt, set_restart_cnt,
        )

    def reset_paradigm_drill_state(self, vocab: list, set_words, set_hist, set_msg, set_cap,
                                    set_entered, set_sub_cnt, set_prev_cnt, set_nxt_cnt) -> None:
        """Reset a hand-rolled paradigm-drill exercise back to its initial state
        (a full multi-field paradigm per word via ``make_paradigm_form``, not
        the one-question-at-a-time ``word_quiz_form``/``word_drill_form``).

        Resets the word queue, history, message, check-snapshot, per-word
        entered values, and check/prev/next click-counter watermarks, for a
        "start over" button. (The per-Enter watermark resets itself, in the
        cell that recreates the paradigm-form widget, once the word queue
        changes.)
        """
        set_words(list(vocab))
        set_hist([])
        set_msg("")
        set_cap(None)
        set_entered({})
        set_sub_cnt(0)
        set_prev_cnt(0)
        set_nxt_cnt(0)

    def dirty_check_button(self, form, cap, cv: "dict | None", attr_name: str, *,
                            word_key: str = "form", label: str = "Check"):
        """Build the "check answer" button for a hand-rolled paradigm-drill
        exercise (full multi-field paradigm per word via
        ``make_paradigm_form``), colored orange ("warn") when the form has unsaved
        changes since the last check.

        ``cv`` is the current word's vocab dict (``None`` when there's no
        current word); ``word_key`` names its identifying field (``"form"``
        for ``load_vocab_tsv``'s schema, e.g. ``word_key="Word"`` for others).
        ``attr_name`` is the snapshot attribute holding the checked word
        ("verb_word" for verbs, "test_word" for nouns, "adj_word" for
        adjectives) — ``cap()``'s snapshot
        must expose that attribute plus a matching ``.value`` list. ``label``
        defaults to English "Check"; pass e.g. ``label="Проверить"`` for a
        localized button.
        """
        live = list(form.widget.values)
        c = cap()
        word = cv[word_key] if cv is not None else None
        has_input = any(v.strip() for v in live)
        match = (
            c is not None
            and word is not None
            and getattr(c, attr_name, None) == word
            and c.value == live
        )
        dirty = has_input and not match
        return self._mo.ui.button(label=label, on_click=_INC, kind="warn" if dirty else "neutral")

    def paradigm_drill_widgets(
        self, *, labels: list, values: "list | None" = None,
        history_len: int = 0, remaining_len: int = 1,
        next_label: "str | None" = None, prev_label: "str | None" = None,
        restart_label: "str | None" = None, lang: str = "ru",
    ) -> tuple:
        """Create the form + nav/restart-button widgets for a hand-rolled
        paradigm-drill exercise (a full multi-field paradigm per word via
        ``make_paradigm_form`` — not the one-question-at-a-time
        ``word_quiz_form``/``word_drill_form``).

        Returns ``(form, prev_btn, nxt_btn, restart_btn)``. Unpack in a
        single cell so marimo tracks ``form`` and re-runs the companion
        ``verb_paradigm_drill_form``/``noun_paradigm_drill_form``/
        ``adjective_paradigm_drill_form`` cell on Enter — that same
        function also handles the restart button's click, so nothing else
        needs to reference ``restart_btn`` except passing it straight
        through. ``labels`` is computed by the caller — static from config
        for verbs, dynamic per-word (pluralia tantum) for nouns via
        ``create_noun_test_ui``.

        ``lang`` (``ru``/``en``/``el``) sets the Next/Prev/Restart button
        text defaults — pass explicit ``next_label``/``prev_label``/
        ``restart_label`` strings only to override those defaults.

        Deliberately does *not* build the check button — call
        :meth:`dirty_check_button` separately, in its own cell. It needs
        ``cap`` (the check snapshot) to color itself, and ``cap`` updates
        on every click/Enter; bundling it here would make *this* cell
        depend on ``cap`` too, rebuilding the form from scratch — losing
        whatever the student just typed and any Enter-triggered
        ``focus_request`` — on every check instead of only when the word
        actually changes. The restart button doesn't have this problem
        (nothing about its own creation depends on ``cap``), so it stays
        bundled here.
        """
        if next_label is None:
            next_label = _PARADIGM_NEXT.get(lang, "Next ▸")
        if prev_label is None:
            prev_label = _PARADIGM_PREV.get(lang, "◂ Prev")
        if restart_label is None:
            restart_label = _PARADIGM_RESTART.get(lang, "↺ Start over")
        form = make_paradigm_form(self._mo, labels, values=values, polytonic=self._cfg.polytonic)
        prev_btn = self._mo.ui.button(label=prev_label, on_click=_INC, disabled=history_len == 0)
        nxt_btn = self._mo.ui.button(label=next_label, on_click=_INC, disabled=remaining_len <= 1)
        restart_btn = self._mo.ui.button(label=restart_label, on_click=_INC)
        return form, prev_btn, nxt_btn, restart_btn

    @staticmethod
    def _pack_paradigm_state(
        get_words, set_words, get_hist, set_hist, get_msg, set_msg,
        get_cap, set_cap, get_entered, set_entered,
        get_sub_cnt, set_sub_cnt, get_prev_cnt, set_prev_cnt,
        get_nxt_cnt, set_nxt_cnt, get_entercnt, set_entercnt,
        get_restart_cnt, set_restart_cnt,
    ) -> dict:
        """Bundle the 10 ``mo.state()`` pairs a paradigm-drill exercise needs
        into one dict, for :meth:`_paradigm_drill_form`'s internal use only.

        Internal-only: never do this bundling in a notebook cell and pass
        the *result* to a different cell — marimo's reactivity is wired by
        statically parsing which names a cell's own source references, so a
        getter read via a dict/attribute lookup in a cell that didn't create
        it directly never triggers a re-run, even though the underlying
        state updates correctly (verified empirically, not assumed — see
        this project's ``CLAUDE.md``). Safe here specifically because both
        the packing and the unpacking happen inside one already-triggered
        cell's call chain (the notebook cell → ``verb_paradigm_drill_form``
        → this → :meth:`_paradigm_drill_form`), never crossing back out to
        a different cell.
        """
        return {
            "words": (get_words, set_words), "hist": (get_hist, set_hist),
            "msg": (get_msg, set_msg), "cap": (get_cap, set_cap),
            "entered": (get_entered, set_entered), "sub_cnt": (get_sub_cnt, set_sub_cnt),
            "prev_cnt": (get_prev_cnt, set_prev_cnt), "nxt_cnt": (get_nxt_cnt, set_nxt_cnt),
            "entercnt": (get_entercnt, set_entercnt), "restart_cnt": (get_restart_cnt, set_restart_cnt),
        }

    def _paradigm_drill_form(
        self,
        state: dict,
        cv: "dict | None", form: Any, check_btn: Any, prev_btn: Any, nxt_btn: Any, restart_btn: Any,
        *,
        vocab: list,
        word_key: str,
        meaning_key: str,
        meaning_label: str,
        title: str,
        done_message: str,
        cap_word_attr: str,
        make_cap: Any,
        slot_ok: Any,
        full_check: Any,
    ) -> Any:
        """Shared engine behind the three public ``*_paradigm_drill_form``
        siblings, which differ only in their POS-specific hooks:
        ``make_cap(live)`` builds the dirty-check snapshot (or returns None
        to skip capturing — each sibling embeds its own capture guard),
        ``cap_word_attr`` names the snapshot attribute holding the checked
        word, ``slot_ok(i, value)`` validates one slot on Enter, and
        ``full_check(cap)`` returns ``(ok, feedback)`` for the whole form.
        Everything else — restart, done-callout, Enter focus-advance,
        save/restore across back/next, and display — is identical across
        parts of speech and lives here.

        ``state`` is the dict built by :meth:`_pack_paradigm_state` — see
        its docstring for why this bundling is only safe internally, never
        across a marimo cell boundary.
        """
        mo = self._mo
        get_words, set_words = state["words"]
        get_hist, set_hist = state["hist"]
        get_msg, set_msg = state["msg"]
        get_cap, set_cap = state["cap"]
        get_entered, set_entered = state["entered"]
        get_sub_cnt, set_sub_cnt = state["sub_cnt"]
        get_prev_cnt, set_prev_cnt = state["prev_cnt"]
        get_nxt_cnt, set_nxt_cnt = state["nxt_cnt"]
        get_entercnt, set_entercnt = state["entercnt"]
        get_restart_cnt, set_restart_cnt = state["restart_cnt"]
        words = get_words()

        if (restart_btn.value or 0) > get_restart_cnt():
            set_restart_cnt(restart_btn.value)
            self.reset_paradigm_drill_state(
                vocab, set_words, set_hist, set_msg, set_cap,
                set_entered, set_sub_cnt, set_prev_cnt, set_nxt_cnt,
            )
            return mo.md("*...*")

        if not words:
            return mo.vstack([mo.callout(mo.md(done_message), kind="success"), restart_btn])

        hist = get_hist()

        _w = form.widget
        _live = list(_w.values)
        _sub_req = _w.submit_request or {}
        _req_id = _sub_req.get("request_id", 0)
        _click = (check_btn.value or 0) > get_sub_cnt()
        _enter = _req_id > get_entercnt()
        if _click or _enter:
            set_sub_cnt(check_btn.value or 0)
            set_entercnt(_req_id)
            snap = make_cap(_live)
            if snap is not None:
                set_cap(snap)
            if _enter and not _click:
                i = _sub_req.get("field_index", -1)
                advance_to = None
                if 0 <= i < len(_live) and slot_ok(i, _live[i]) and i + 1 < len(_live):
                    advance_to = i + 1
                # Always reply, even on a wrong answer or the last field --
                # the JS side locks the origin field the instant Enter
                # fires and only releases it once this exact request_id
                # comes back, so a dropped reply would leave it stuck.
                _w.focus_request = {"request_id": _req_id, "advance_to": advance_to}

        cap = get_cap()
        ok = False
        fb = ""
        if cv and cap and getattr(cap, cap_word_attr, None) == cv[word_key]:
            ok, fb = full_check(cap)

        if ok:
            set_entered(self.save_entry(get_entered(), cv, form, word_key=word_key))
            set_hist(hist + [cv])
            set_words([w for w in words if w[word_key] != cv[word_key]])
            set_msg(f"✓ {cv[word_key]} — {cv[meaning_key]}")
            set_cap(None)
            return mo.md("*...*")

        if (nxt_btn.value or 0) > get_nxt_cnt():
            set_nxt_cnt(nxt_btn.value)
            set_entered(self.save_entry(get_entered(), cv, form, word_key=word_key))
            set_cap(None)
            set_sub_cnt(0)
            if words and cv:
                set_hist(hist + [cv])
                set_words([w for w in words if w[word_key] != cv[word_key]])
            return mo.md("*...*")

        if (prev_btn.value or 0) > get_prev_cnt():
            set_prev_cnt(prev_btn.value)
            set_entered(self.save_entry(get_entered(), cv, form, word_key=word_key))
            set_cap(None)
            set_sub_cnt(0)
            if hist:
                prev_word = hist[-1]
                set_hist(hist[:-1])
                set_words([prev_word] + [w for w in words if w[word_key] != prev_word[word_key]])
            return mo.md("*...*")

        _done_count = len(vocab) - len(words)
        _pfx = f"{title}\n\n" if title else ""
        items = [mo.md(f"{_pfx}**{_done_count + 1}** / {len(vocab)}")]
        _msg = get_msg()
        if _msg:
            items.append(mo.md(_msg))
        items.append(mo.md(f"{meaning_label}: **{cv[meaning_key]}**") if cv else mo.md(""))
        items.append(form)
        items.append(mo.hstack([check_btn, prev_btn, nxt_btn], justify="end"))
        items.append(mo.md(fb) if fb else mo.md(""))
        return mo.vstack(items)

    def verb_paradigm_drill_form(
        self,
        get_words, set_words,
        get_hist, set_hist,
        get_msg, set_msg,
        get_cap, set_cap,
        get_entered, set_entered,
        get_sub_cnt, set_sub_cnt,
        get_prev_cnt, set_prev_cnt,
        get_nxt_cnt, set_nxt_cnt,
        get_entercnt, set_entercnt,
        get_restart_cnt, set_restart_cnt,
        cv: "dict | None", form: Any, check_btn: Any, prev_btn: Any, nxt_btn: Any, restart_btn: Any,
        *,
        vocab: list,
        tense: str = "present",
        word_key: str = "form",
        meaning_key: str = "meaning",
        meaning_label: str = "Meaning",
        title: str = "",
        done_message: str = "Done — every verb drilled!",
    ) -> Any:
        """Unified verb-paradigm drill: per-field Enter-navigation, dirty-check
        snapshot, save/restore across back/next, restart, and full display,
        in one call.

        Companion to :meth:`paradigm_drill_widgets`. Place in the cell after
        the state and widgets cells — replaces the snapshot, full-check,
        correct-handler, next/prev-handler, restart-handler, and display
        cells a hand-rolled version of this exercise would otherwise need.
        """
        state = self._pack_paradigm_state(
            get_words, set_words, get_hist, set_hist, get_msg, set_msg,
            get_cap, set_cap, get_entered, set_entered,
            get_sub_cnt, set_sub_cnt, get_prev_cnt, set_prev_cnt,
            get_nxt_cnt, set_nxt_cnt, get_entercnt, set_entercnt,
            get_restart_cnt, set_restart_cnt,
        )
        return self._paradigm_drill_form(
            state, cv, form, check_btn, prev_btn, nxt_btn, restart_btn,
            vocab=vocab, word_key=word_key, meaning_key=meaning_key,
            meaning_label=meaning_label, title=title, done_message=done_message,
            cap_word_attr="verb_word",
            make_cap=lambda live: (
                SimpleNamespace(verb_word=cv[word_key], tense=tense, value=live)
                if cv else None),
            slot_ok=lambda i, v: bool(cv) and self.check_verb_slot(cv[word_key], tense, i, v),
            full_check=lambda cap: self.check_verb_test(cv[word_key], cap, tense),
        )

    def noun_paradigm_drill_form(
        self,
        get_words, set_words,
        get_hist, set_hist,
        get_msg, set_msg,
        get_cap, set_cap,
        get_entered, set_entered,
        get_sub_cnt, set_sub_cnt,
        get_prev_cnt, set_prev_cnt,
        get_nxt_cnt, set_nxt_cnt,
        get_entercnt, set_entercnt,
        get_restart_cnt, set_restart_cnt,
        cv: "dict | None", form: Any, check_btn: Any, prev_btn: Any, nxt_btn: Any, restart_btn: Any,
        *,
        vocab: list,
        noun_meta: Any,
        article: bool = True,
        indefinite: bool = False,
        word_key: str = "form",
        meaning_key: str = "meaning",
        meaning_label: str = "Meaning",
        title: str = "",
        done_message: str = "Done — every noun drilled!",
    ) -> Any:
        """Unified noun-paradigm drill — sibling of :meth:`verb_paradigm_drill_form`
        (see its docstring for the shared design). Uses ``check_noun_slot``/
        ``check_noun_test`` instead, and needs ``noun_meta`` (from
        :meth:`noun_drill_meta`, also the 3rd return value of
        :meth:`create_noun_test_ui`) for its ``active_cases``/
        ``is_pluralia_tantum`` — nouns' active cases vary per word (pluralia
        tantum), unlike a verb's fixed slot list.

        ``article``: ``True`` (default) requires the definite article in
        each slot's answer (e.g. Ancient Greek drills always want this).
        ``False`` checks the bare noun form only — pass ``mode_selector.value
        == 'article'`` (or equivalent) to let a notebook toggle between the
        two, e.g. for a Modern Greek course offering both a "simple" and an
        "article" noun-test mode.

        ``indefinite``: ``False`` (default). ``True`` expects ``form`` to
        carry extra slots after the definite ones — one per singular case
        (indefinite articles don't inflect for plural) — each always
        requiring the indefinite article, independent of ``article``. Build
        the matching label list as ``gu.noun_slot_labels(active_cases) +
        [f"Ind. {l}" for l in gu.noun_slot_labels(gu.noun_indef_cells(active_cases))]``
        before constructing ``form``. No-ops (no extra slots expected) when
        ``config.indef_articles`` is unset (e.g. Ancient Greek) — safe to
        pass unconditionally from a notebook that doesn't check the config
        itself.
        """
        active_cases = getattr(noun_meta, "active_cases", [])
        state = self._pack_paradigm_state(
            get_words, set_words, get_hist, set_hist, get_msg, set_msg,
            get_cap, set_cap, get_entered, set_entered,
            get_sub_cnt, set_sub_cnt, get_prev_cnt, set_prev_cnt,
            get_nxt_cnt, set_nxt_cnt, get_entercnt, set_entercnt,
            get_restart_cnt, set_restart_cnt,
        )
        return self._paradigm_drill_form(
            state, cv, form, check_btn, prev_btn, nxt_btn, restart_btn,
            vocab=vocab, word_key=word_key, meaning_key=meaning_key,
            meaning_label=meaning_label, title=title, done_message=done_message,
            cap_word_attr="test_word",
            make_cap=lambda live: (
                SimpleNamespace(
                    test_word=cv[word_key],
                    is_pluralia_tantum=getattr(noun_meta, "is_pluralia_tantum", False),
                    active_cases=active_cases,
                    value=live,
                )
                if cv is not None and noun_meta is not None and live else None),
            slot_ok=lambda i, v: (
                cv is not None and noun_meta is not None
                and self.check_noun_slot(cv[word_key], i, v, article=article,
                                          active_cases=active_cases, indefinite=indefinite)),
            full_check=lambda cap: self.check_noun_test(cv[word_key], cap, article=article, indefinite=indefinite),
        )

    def adjective_paradigm_drill_form(
        self,
        get_words, set_words,
        get_hist, set_hist,
        get_msg, set_msg,
        get_cap, set_cap,
        get_entered, set_entered,
        get_sub_cnt, set_sub_cnt,
        get_prev_cnt, set_prev_cnt,
        get_nxt_cnt, set_nxt_cnt,
        get_entercnt, set_entercnt,
        get_restart_cnt, set_restart_cnt,
        cv: "dict | None", form: Any, check_btn: Any, prev_btn: Any, nxt_btn: Any, restart_btn: Any,
        *,
        vocab: list,
        mode: str = "simple",
        word_key: str = "form",
        meaning_key: str = "meaning",
        meaning_label: str = "Meaning",
        title: str = "",
        done_message: str = "Done — every adjective drilled!",
    ) -> Any:
        """Unified adjective-paradigm drill — sibling of :meth:`verb_paradigm_drill_form`
        (see its docstring for the shared design). Uses ``check_adjective_slot``/
        ``check_adjective_test`` instead; ``mode`` picks the slot set
        (``"simple"`` = nominative only, 6 slots; anything else = every
        case in ``config.adj_cases``), matching :meth:`adjective_slot_labels`'s
        labels for the same mode.
        """
        state = self._pack_paradigm_state(
            get_words, set_words, get_hist, set_hist, get_msg, set_msg,
            get_cap, set_cap, get_entered, set_entered,
            get_sub_cnt, set_sub_cnt, get_prev_cnt, set_prev_cnt,
            get_nxt_cnt, set_nxt_cnt, get_entercnt, set_entercnt,
            get_restart_cnt, set_restart_cnt,
        )
        return self._paradigm_drill_form(
            state, cv, form, check_btn, prev_btn, nxt_btn, restart_btn,
            vocab=vocab, word_key=word_key, meaning_key=meaning_key,
            meaning_label=meaning_label, title=title, done_message=done_message,
            cap_word_attr="adj_word",
            make_cap=lambda live: (
                SimpleNamespace(adj_word=cv[word_key], adj_mode=mode, value=live)
                if cv else None),
            slot_ok=lambda i, v: bool(cv) and self.check_adjective_slot(cv[word_key], mode, i, v),
            full_check=lambda cap: self.check_adjective_test(cv[word_key], cap, mode),
        )

    def _handle_prev(self, cv, restore_entry, history, future, score,
                     set_cv, set_history, set_future, set_score, set_restore, mo) -> Any:
        """Shared Prev-button handler for word-drill and word-quiz forms."""
        if history:
            *rest, last = history
            set_future([self._make_future_entry(cv, restore_entry)] + future)
            set_cv(last["word"])
            set_score({"correct": score["correct"] - int(last["correct"]), "total": score["total"] - 1})
            set_history(rest)
            set_restore({"answer": last["answer"], "correct": last["correct"]})
        return mo.md("*...*")

    def _handle_quiz_next(self, all_items, cv, ans, correct, remaining, restore_entry,
                          history, future, score,
                          set_cv, set_remaining, set_history, set_future, set_score, set_restore,
                          mo) -> "Any | None":
        """Shared Next-button handler for stanza-match and translation-presence forms.

        Handles restart-after-done, forward-through-history, and normal-advance.
        Returns the "please wait" placeholder for any of those three; returns
        ``None`` when there's no selection yet, so the caller falls through and
        re-renders as-is (mirrors :meth:`_handle_prev`'s shape, but Next has a
        third case Prev doesn't: nothing selected yet).
        """
        if cv is None:  # restart after done
            self._restart_quiz(all_items, set_cv, set_remaining,
                                set_score, set_history, set_future, set_restore)
            return mo.md("*...*")
        if future:  # forward through history
            _next = future[0]
            _a = ans if ans is not None else (restore_entry.get("answer") if restore_entry else None)
            _ok = (_a == correct) if _a is not None else False
            set_history(history + [{"word": cv, "answer": _a, "correct": _ok}])
            set_score({"correct": score["correct"] + int(_ok), "total": score["total"] + 1})
            set_future(future[1:])
            set_cv(_next["word"])
            set_restore(
                {"answer": _next["answer"], "correct": _next["correct"]}
                if _next["correct"] is not None else None
            )
            return mo.md("*...*")
        if ans is not None:  # normal advance
            _ok = ans == correct
            set_history(history + [{"word": cv, "answer": ans, "correct": _ok}])
            set_score({"correct": score["correct"] + int(_ok), "total": score["total"] + 1})
            set_cv(remaining[0] if remaining else None)
            set_remaining(remaining[1:] if remaining else [])
            set_restore(None)
            return mo.md("*...*")
        return None  # no selection — caller falls through and re-renders as-is

    @staticmethod
    def word_drill_done(cv: "dict | None", remaining: "list | None") -> bool:
        """True once a drill/quiz is exhausted: no current word, queue empty.

        Used internally by :meth:`word_drill_widgets`, :meth:`word_quiz_widgets`,
        :meth:`stanza_match_widgets`, and :meth:`translation_presence_widgets`
        (each already takes ``cv``/``remaining`` and derives ``done`` itself) —
        callers don't need to call this directly for that purpose. Pass the
        already-called state values, not getters, if calling it directly for
        some other reason.
        """
        return cv is None and remaining is not None and len(remaining) == 0

    def word_drill_widgets(
        self,
        *,
        cv: "dict | None",
        remaining: "list | None",
        restore_entry: "dict | None" = None,
        history_len: int = 0,
        placeholder: "str | None" = None,
        label: "str | None" = None,
        lang: str = "ru",
    ) -> tuple:
        """Create all widgets for a word-drill exercise.

        Returns ``(write_input, dia_reactive, check_btn, prev_btn, next_btn)``.
        Unpack in a single cell so marimo tracks ``dia_reactive`` and re-runs
        the display cell when Enter is pressed. ``lang`` (``ru``/``en``/``el``)
        sets the Next/Prev button text and the defaults for ``placeholder``
        and ``label`` (the Check button's text) — pass explicit strings only
        to override those defaults. ``cv``/``remaining`` are the already-called
        state values (see :meth:`word_drill_done`) — used only to derive
        whether the drill is finished, for the Next/Prev button labels. Use
        the same ``lang`` as the companion :meth:`word_drill_form` call.
        """
        mo = self._mo
        if placeholder is None:
            placeholder = _WRITE_PLACEHOLDER.get(lang, "Greek word…")
        if label is None:
            label = _CHECK_LABEL.get(lang, "Check")
        _ans = (restore_entry.get("answer") or "") if restore_entry else ""
        write_input = self.diacritics_text(placeholder=placeholder, value=_ans)
        dia = write_input._ui
        check_btn = mo.ui.button(label=label, on_click=_INC)
        _done = self.word_drill_done(cv, remaining)
        next_btn, prev_btn = self._make_nav_buttons(done=_done, history_len=history_len, lang=lang)
        return write_input, dia, check_btn, prev_btn, next_btn

    def word_drill_display(
        self,
        cv: "dict | None",
        remaining: "list | None",
        score: dict,
        restore_entry: "dict | None",
        write_input: Any,
        dia_reactive: Any,
        check_btn: Any,
        prev_btn: Any,
        next_btn: Any,
        *,
        vocab: list,
        title: str = "",
        comment: str = "",
        meaning_key: str = "meaning",
        form_key: str = "form",
        lang: str = "ru",
    ) -> Any:
        """Render the write-the-word drill UI with history navigation.

        The calling cell must reference ``dia_reactive`` directly so marimo
        re-runs it when ``enter_pressed`` changes.

        Args:
            cv:            Current word dict (``None`` = not started or done).
            remaining:     Remaining word list from state.
            score:         ``{"correct": int, "total": int}`` from state.
            restore_entry: ``{"answer": str, "correct": bool}`` when browsing
                           history, else ``None``.
            write_input:   Diacritics-text widget (from :meth:`diacritics_text`).
            dia_reactive:  ``write_input._ui`` — the underlying
                           ``mo.ui.anywidget`` that triggers cell re-runs.
            check_btn:     "Проверить" button.
            prev_btn:      "Предыдущий" button.
            next_btn:      "Следующий" / "Пройти снова" button.
            vocab:         Full word list (for total-count display).
            title:         Markdown heading rendered above the comment.
            comment:       Optional note (use ``<br>`` for tight line breaks).
            meaning_key:   Key in each word dict used as the prompt.
            form_key:      Key in each word dict for the expected answer.
            lang:          UI language for the done-screen and progress line's
                           "correct" label (``ru``/``en``/``el``).
        """
        mo = self._mo
        _done = self.word_drill_done(cv, remaining)
        if _done:
            self._quiz_done_stop(score, lang, next_btn=next_btn)
        _meaning = cv.get(meaning_key, "") if cv is not None else ""
        _typed = write_input.value.strip()
        _enter = dia_reactive.value.get("enter_pressed", 0)
        _check = (check_btn.value or _enter) and _typed and cv is not None
        if _check:
            fb = self._feedback_md(mo, self._ci(_typed, {cv[form_key]}), _meaning, cv[form_key])
        elif restore_entry is not None:
            fb = self._feedback_md(mo, restore_entry["correct"], _meaning, cv[form_key])
        else:
            fb = mo.md(f"*{_meaning}*") if _meaning else mo.md("")
        parts: list = []
        if title:
            parts.append(mo.md(title))
        if comment:
            parts.append(mo.md(comment))
        _corr = _QUIZ_PROGRESS_CORR.get(lang, "correct")
        parts.append(mo.md(f"**{score['total'] + 1}** / {len(vocab)} — {_corr}: {score['correct']}"))
        return mo.vstack(parts + [
            fb,
            write_input,
            mo.hstack([check_btn, prev_btn, next_btn], justify="start"),
        ])

    def word_drill_form(
        self,
        get_cv, set_cv,
        get_remaining, set_remaining,
        get_score, set_score,
        get_restore, set_restore,
        get_history, set_history,
        get_future, set_future,
        write_input: Any,
        dia_reactive: Any,
        check_btn: Any,
        prev_btn: Any,
        next_btn: Any,
        *,
        vocab: list,
        title: str = "",
        comment: str = "",
        meaning_key: str = "meaning",
        form_key: str = "form",
        lang: str = "ru",
    ) -> Any:
        """Unified word-drill: initialization, navigation, and display in one call.

        Replaces the separate init cell, handler cell, and display cell with a
        single function call. Place after the state cell and widget cell.

        Pass ``mo.state`` getter/setter pairs directly — getters are called
        internally so marimo tracks the reactive dependencies.

        Args:
            get_cv / set_cv: state pair for the current word dict.
            get_remaining / set_remaining: state pair for remaining word list.
            get_score / set_score: state pair for ``{"correct": int, "total": int}``.
            get_restore / set_restore: state pair for history-review entry.
            get_history / set_history: state pair for the answered-words stack.
            get_future / set_future: state pair for forward-navigation stack.
            write_input: Diacritics-text widget (from :meth:`word_drill_widgets`).
            dia_reactive: ``write_input._ui`` — tracks Enter key presses.
            check_btn: "Проверить" button.
            prev_btn: "Предыдущий" button.
            next_btn: "Следующий" / "Пройти снова" button.
            vocab: Full word list; used for restart shuffle and total count.
            title: Markdown heading rendered above the exercise.
            comment: Optional note (use ``<br>`` for tight line breaks).
            meaning_key: Key in each word dict used as the prompt.
            form_key: Key in each word dict for the expected answer.
            lang: UI language for the done-screen and progress line's "correct"
                  label (``ru``/``en``/``el``).
        """
        mo = self._mo
        cv = get_cv()
        remaining = get_remaining()
        score = get_score()
        restore_entry = get_restore()
        history = get_history()
        future = get_future()

        # Initialize on first run (remaining is None = not yet started)
        if remaining is None:
            if vocab:
                self._shuffle_start(vocab, set_cv, set_remaining)
            return mo.md("*...*")

        # Handle Next button
        if next_btn.value:
            if cv is None:  # restart after done
                self._restart_quiz(vocab, set_cv, set_remaining,
                                    set_score, set_history, set_future, set_restore)
            elif future:  # forward through history
                _re = restore_entry
                _next = future[0]
                _ans = (write_input.value.strip() or (_re.get("answer") or "")) if _re else write_input.value.strip()
                _ok = self._ci(_ans, {cv[form_key]}) if _ans else False
                set_history(history + [{"word": cv, "answer": _ans, "correct": _ok}])
                set_score({"correct": score["correct"] + int(_ok), "total": score["total"] + 1})
                set_future(future[1:])
                set_cv(_next["word"])
                set_restore(
                    {"answer": _next["answer"], "correct": _next["correct"]}
                    if _next["correct"] is not None else None
                )
            else:  # normal advance
                _typed = write_input.value.strip()
                _ok = self._ci(_typed, {cv[form_key]})
                set_history(history + [{"word": cv, "answer": _typed, "correct": _ok}])
                set_score({"correct": score["correct"] + int(_ok), "total": score["total"] + 1})
                set_cv(remaining[0] if remaining else None)
                set_remaining(remaining[1:] if remaining else [])
                set_restore(None)
            return mo.md("*...*")

        # Handle Prev button
        if prev_btn.value:
            return self._handle_prev(cv, restore_entry, history, future, score,
                                     set_cv, set_history, set_future, set_score, set_restore, mo)

        return self.word_drill_display(
            cv, remaining, score, restore_entry,
            write_input, dia_reactive, check_btn, prev_btn, next_btn,
            vocab=vocab, title=title, comment=comment,
            meaning_key=meaning_key, form_key=form_key, lang=lang,
        )

    # ------------------------------------------------------- word-form quiz

    def _get_meaning(self, word: dict, lang: str) -> str:
        """Extract the right-language meaning from a word dict."""
        return word.get(
            "meaning" if lang == "ru" else f"meaning_{lang}",
            word.get("meaning", ""),
        )

    def _quiz_done_stop(self, score_dict: dict, lang: str, *, next_btn: Any = None) -> None:
        """Call mo.stop with the standard done-screen (shared by all quiz/drill types).

        next_btn: optional restart button embedded in the done-screen vstack
        (word_drill_display/word_quiz_form pass their own; word_quiz_feedback's
        caller renders next_btn separately, so it stays out of the callout there).
        """
        mo = self._mo
        _done_msg = _QUIZ_DONE.get(lang, "Done!").format(btn=_NAV_AGAIN.get(lang, "Again"))
        content = [
            mo.callout(mo.md(_done_msg), kind="success"),
            mo.md(f"{_QUIZ_CORR.get(lang, 'Correct:')} **{score_dict['correct']}** / **{score_dict['total']}**"),
        ]
        if next_btn is not None:
            content.append(next_btn)
        mo.stop(True, mo.vstack(content))

    def word_quiz_question(
        self,
        word: "dict | None",
        all_words: "list[dict]",
        lang: str,
        rng: Any,
        *,
        initial_value: "str | None" = None,
    ) -> "tuple":
        """Build a radio-button question for a word-form quiz (Odyssey-style).

        Args:
            word:      Current word dict from state (cv()); None when quiz not started.
            all_words: Full word list used to sample up to 3 distractor forms.
            lang:      UI language (``"ru"``, ``"en"``, or ``"el"``).
            rng:       The ``random`` module from the calling cell.

        Returns ``(answer_radio, word)``.  Calls ``mo.stop`` when *word* is None
        so the cell halts cleanly.

        Required word dict key: ``"form"``. Optional: ``"context"`` (shown
        alongside the meaning when present — absent for flat vocab from
        :meth:`load_vocab_tsv`), ``"meaning"``/``"meaning_en"``/``"meaning_el"``.
        """
        mo = self._mo
        if word is None:
            mo.stop(True, mo.md(""))

        _meaning = self._get_meaning(word, lang)
        other_forms = list({q["form"] for q in all_words if q["form"] != word["form"]})
        choices = sorted([word["form"]] + other_forms[:3], key=lambda x: rng.random())
        _ctx = word.get("context", "")
        _ctx_part = f" — _{_ctx}_" if _ctx else ""
        _kw = {"value": initial_value} if initial_value is not None and initial_value in choices else {}
        radio = mo.ui.radio(
            options=choices,
            label=f"«{_meaning}»{_ctx_part}\n\n{_QUIZ_FORM_LBL.get(lang, 'Form in text:')}",
            **_kw,
        )
        return radio, word

    def word_quiz_feedback(
        self,
        w: "dict | None",
        answer_value: "str | None",
        score_dict: dict,
        lang: str,
        *,
        build_paradigm_table: "Any | None" = None,
    ) -> Any:
        """Build feedback for a word-form quiz answer.

        Args:
            w:                     Current word dict; None when all words exhausted.
            answer_value:          Selected radio value; None if not yet answered.
            score_dict:            ``{"correct": int, "total": int}`` from score state.
            lang:                  UI language (``"ru"``, ``"en"``, or ``"el"``).
            build_paradigm_table:  Optional ``(word_dict, lang=lang) -> str | None``
                                   returning an HTML paradigm table string.

        Returns a marimo element.  Calls ``mo.stop`` with a done-screen when *w*
        is None and at least one card has been answered.

        ``w["form"]`` is the surface form being tested; ``w["lemma"]`` is the
        dictionary/citation form used for lookup and paradigm generation. For
        flat vocab (:meth:`load_vocab_tsv`), ``lemma`` is absent and falls back
        to ``form`` here. For inflected-text vocab, ``lemma`` may legitimately
        differ (e.g. surface form ``ἔγνω`` from lemma ``γιγνώσκω``) — that's
        when the "form → lemma" feedback line is shown instead of just "form".
        """
        mo = self._mo

        if w is None:
            if score_dict.get("total", 0) > 0:
                self._quiz_done_stop(score_dict, lang)
            return mo.md("")

        if answer_value is None:
            return mo.md("")

        pos_lbl   = _QUIZ_POS.get(lang, _QUIZ_POS["en"]).get(w.get("pos", ""), w.get("pos", ""))
        gram_lbl  = w.get("grammar_label") or fmt_ud_feats(w.get("grammar", ""), lang)
        gram_line = " · ".join(filter(None, [pos_lbl, gram_lbl]))

        form = w["form"]
        lemma = _lemma_of(w, form)
        word_info = f"**{form}**" if form == lemma else f"**{form}** → **{lemma}**"
        correct = answer_value == form

        if correct:
            tbl = mo.md("")
            if build_paradigm_table is not None:
                html, err = self._render_table_or_error(build_paradigm_table, w, lang)
                tbl = mo.md(f"_{err}_") if err else (mo.Html(html) if html else mo.md(""))
            return mo.callout(
                mo.vstack([
                    mo.md(_QUIZ_RIGHT.get(lang, "✓")),
                    mo.md(f"{word_info} · {gram_line}"),
                    tbl,
                ]),
                kind="success",
            )
        return mo.callout(
            mo.vstack([
                mo.md(f"{_QUIZ_WRONG.get(lang, '✗')} **{form}**"),
                mo.md(f"{word_info} · {gram_line}"),
            ]),
            kind="danger",
        )

    def word_quiz_widgets(
        self,
        *,
        cv: "dict | None",
        remaining: "list | None",
        vocab: list,
        restore_entry: "dict | None" = None,
        history_len: int = 0,
        lang: str = "ru",
    ) -> tuple:
        """Create widgets for a multiple-choice word-quiz exercise.

        Returns ``(answer_radio, next_btn, prev_btn)``.
        Unpack in a single cell so marimo tracks ``answer_radio`` and re-runs
        the form cell when the user selects an option. ``lang`` sets the
        radio's own label text (``ru``/``en``/``el``) — pass the same value
        given to the companion :meth:`word_quiz_form` call. ``remaining`` is
        the already-called state value (see :meth:`word_drill_done`) — used
        only alongside ``cv`` to derive whether the quiz is finished, for the
        Next/Prev button labels.
        """
        if cv is None:
            answer_radio = self._mo.ui.radio(options=[""])
        else:
            _restore = restore_entry.get("answer") if restore_entry else None
            answer_radio, _ = self.word_quiz_question(cv, vocab, lang, _random, initial_value=_restore)
        _done = self.word_drill_done(cv, remaining)
        next_btn, prev_btn = self._make_nav_buttons(done=_done, history_len=history_len, lang=lang)
        return answer_radio, next_btn, prev_btn

    def word_quiz_form(
        self,
        get_cv, set_cv,
        get_remaining, set_remaining,
        get_score, set_score,
        get_restore, set_restore,
        get_history, set_history,
        get_future, set_future,
        answer_radio: Any,
        next_btn: Any,
        prev_btn: Any,
        *,
        vocab: list,
        title: str = "",
        meaning_key: str = "meaning",
        form_key: str = "form",
        lang: str = "ru",
        build_paradigm_table: "Any | None" = None,
        renew_btn: "Any | None" = None,
    ) -> Any:
        """Unified multiple-choice quiz: initialization, navigation, and display.

        Companion to :meth:`word_quiz_widgets`.  Place in the cell after the
        state and widget cells.

        Feedback appears immediately when the user selects a radio option;
        clicking "Следующий" advances to the next word.  If "Следующий" is
        clicked before a selection is made the cell re-renders in place without
        advancing.

        Args:
            get_cv / set_cv: state pair for the current word dict.
            get_remaining / set_remaining: state pair for remaining word list.
            get_score / set_score: state pair for ``{"correct": int, "total": int}``.
            get_restore / set_restore: state pair for history-review entry.
            get_history / set_history: state pair for the answered-words stack.
            get_future / set_future: state pair for forward-navigation stack.
            answer_radio: ``mo.ui.radio`` from :meth:`word_quiz_widgets`.
            next_btn: "Следующий" / "Пройти снова" button.
            prev_btn: "Предыдущий" button.
            vocab: Full word list; used for restart shuffle and total count.
            title: Markdown heading with optional progress line.
            meaning_key: Key in each word dict used as the radio label prompt.
            form_key: Key in each word dict for the correct answer form.
            lang: UI language — passed to ``build_paradigm_table`` and used for
                  the progress line's "correct" label (``ru``/``en``/``el``).
            build_paradigm_table: Optional ``(word_dict, lang=lang) -> str | None``
                                   returning an HTML paradigm table. Shown under
                                   the feedback line, only on a correct answer.
            renew_btn: Optional extra button (e.g. "draw a new random set")
                       shown alongside prev/next — this function only renders
                       it, the caller's own cell wires what it does on click.
        """
        mo = self._mo
        cv = get_cv()
        remaining = get_remaining()
        score = get_score()
        restore_entry = get_restore()
        history = get_history()
        future = get_future()

        # Initialize on first run
        if remaining is None:
            if vocab:
                self._shuffle_start(vocab, set_cv, set_remaining)
            return mo.md("*...*")

        _done = self.word_drill_done(cv, remaining)
        _ans = answer_radio.value

        # Handle Next button
        if next_btn.value:
            if cv is None:  # restart after done
                self._restart_quiz(vocab, set_cv, set_remaining,
                                    set_score, set_history, set_future, set_restore)
                return mo.md("*...*")
            elif future:  # forward through history
                _re = restore_entry
                _next = future[0]
                _a = _ans if _ans is not None else (_re.get("answer") if _re else None)
                _ok = (_a == cv[form_key]) if _a is not None else False
                set_history(history + [{"word": cv, "answer": _a, "correct": _ok}])
                set_score({"correct": score["correct"] + int(_ok), "total": score["total"] + 1})
                set_future(future[1:])
                set_cv(_next["word"])
                set_restore(
                    {"answer": _next["answer"], "correct": _next["correct"]}
                    if _next["correct"] is not None else None
                )
                return mo.md("*...*")
            elif _ans is not None:  # normal advance
                _ok = _ans == cv[form_key]
                set_history(history + [{"word": cv, "answer": _ans, "correct": _ok}])
                set_score({"correct": score["correct"] + int(_ok), "total": score["total"] + 1})
                set_cv(remaining[0] if remaining else None)
                set_remaining(remaining[1:] if remaining else [])
                set_restore(None)
                return mo.md("*...*")
            # else: no selection — fall through and re-render as-is

        # Handle Prev button
        if prev_btn.value:
            return self._handle_prev(cv, restore_entry, history, future, score,
                                     set_cv, set_history, set_future, set_score, set_restore, mo)

        # Display
        if _done:
            self._quiz_done_stop(score, lang, next_btn=next_btn)

        _fb_ans = _ans if _ans is not None else (restore_entry["answer"] if restore_entry else None)
        if _fb_ans is not None:
            _ok = _fb_ans == cv[form_key]
            fb = self._feedback_md(mo, _ok, cv[meaning_key], cv[form_key])
            if _ok and build_paradigm_table is not None:
                html, err = self._render_table_or_error(build_paradigm_table, cv, lang)
                if err:
                    fb = mo.vstack([fb, mo.md(f"_{err}_")])
                elif html:
                    fb = mo.vstack([fb, mo.Html(html)])
                else:
                    _lemma = _lemma_of(cv, cv[form_key])
                    fb = mo.vstack([fb, mo.md(f"_{cv[form_key]} — отсутствует в парадигме {_lemma}_")])
        else:
            fb = mo.md("")
        _pfx = f"{title}\n\n" if title else ""
        _corr = _QUIZ_PROGRESS_CORR.get(lang, "correct")
        progress = mo.md(f"{_pfx}**{score['total'] + 1}** / {len(vocab)} — {_corr}: {score['correct']}")
        return mo.vstack([progress, answer_radio, fb, self._nav_row(prev_btn, next_btn, renew_btn)])

    # ------------------------------------------------------- stanza-match quiz (5a)

    def _stanza_match_pick_translation(self, stanza: dict) -> "tuple[str, str] | None":
        """One non-placeholder ``(translator, text)`` pair for this stanza.

        Picked via a ref-seeded ``random.Random`` instance rather than always
        taking dict order's first entry, so across a set of stanzas attribution
        is a balanced mix of every translator available for each stanza,
        instead of always the same one (e.g. always "подстрочник", the
        translator that happens to sort first in every stanza's dict).

        Still a pure function of *stanza* alone — no external counter or
        shared RNG state. Seeding a local ``Random`` with the ref string is
        deterministic across processes (unlike Python's own salted `hash()`),
        so the same stanza always yields the same pick, and
        :meth:`stanza_match_widgets` (building options) and
        :meth:`stanza_match_form` (grading) independently agree without
        sharing any state.
        """
        candidates = [(tr, txt) for tr, txt in stanza.get("translations", {}).items()
                      if txt and txt != "—"]
        if not candidates:
            return None
        return _random.Random(stanza["ref"]).choice(candidates)

    @staticmethod
    def _blockquote_cite(text: str, attribution: str) -> str:
        """"> text\\n> — attribution" Markdown blockquote citation, shared by
        :meth:`_stanza_match_attribute_prompt` and :meth:`_presence_passage_md`."""
        return f"> {text}\n> — {attribution}"

    def _stanza_match_attribute_prompt(self, text: str, translator: "str | None") -> str:
        """Blockquote-cite a translation shown as the stanza-match prompt."""
        if not translator:
            return text
        return self._blockquote_cite(text, translator)

    @staticmethod
    def _stanza_match_attribute_option(text: str, translator: "str | None") -> str:
        """Inline-suffix a translation shown as a stanza-match answer option.
        Applied to every option (correct and distractors alike) so no
        option is singled out by having, or lacking, attribution."""
        if not translator:
            return text
        return f"{text} — {translator}"

    def _stanza_match_prompt_and_correct(self, stanza: dict, direction: str,
                                          *, _picked: "tuple[str, str] | None" = ...) -> "tuple[str, str]":
        """Pure ``(prompt, correct_answer)`` pair for one stanza + direction.

        No randomness: the same ``(stanza, direction)`` always yields the same
        pair, so :meth:`stanza_match_widgets` (building the option list) and
        :meth:`stanza_match_form` (grading) independently agree on the correct
        answer without sharing any state — grading only ever needs this pair,
        never the distractor set.

        Whichever side is a translation is attributed to its translator:
        the prompt (blockquote-cited) in ``"tr_to_grc"``, the correct answer
        (inline-suffixed, matching :meth:`_stanza_match_round`'s distractor
        formatting) in ``"grc_to_tr"``.

        *_picked*: internal escape hatch for :meth:`_stanza_match_round`,
        which already needs :meth:`_stanza_match_pick_translation`'s raw
        result for its own veto logic and passes it here to avoid picking
        twice. Leave unset to have it computed here as usual.
        """
        grc_text = "\n".join(stanza["lines"])
        picked = self._stanza_match_pick_translation(stanza) if _picked is ... else _picked
        translator, tr_text = picked if picked else (None, "")
        if direction == "grc_to_tr":
            return grc_text, self._stanza_match_attribute_option(tr_text, translator)
        return self._stanza_match_attribute_prompt(tr_text, translator), grc_text

    def _stanza_match_distractor_pool(self, stanza: dict, all_stanzas: "list[dict]",
                                       direction: str) -> "list[tuple[str, str | None, str]]":
        """``(ref, translator, candidate_text)`` triples from OTHER stanzas,
        answer-side of *direction* (their translations for ``grc_to_tr`` --
        *translator* is that candidate's own, since distractors are pooled
        across every translator, not just each stanza's picked one; their
        Greek text for ``tr_to_grc``, *translator* always ``None``)."""
        others = [s for s in all_stanzas if s["ref"] != stanza["ref"]]
        if direction == "grc_to_tr":
            return [(s["ref"], tr, txt) for s in others
                    for tr, txt in s.get("translations", {}).items() if txt and txt != "—"]
        return [(s["ref"], None, "\n".join(s["lines"])) for s in others]

    def _stanza_match_round(self, stanza: dict, all_stanzas: "list[dict]", direction: str,
                             rng: Any, *, n_options: int = 3) -> dict:
        """Build one stanza-match round for display: a prompt + n_options
        candidate texts (1 correct + distractors from OTHER stanzas).

        In ``"grc_to_tr"``, each distractor is drawn from a different
        translator than the correct answer's (and than each other), so a
        round with as many options as live translators shows every
        translator exactly once instead of favoring whichever translator
        happens to be listed first across the other stanzas.

        Returns ``{"prompt": str, "options": list[str], "correct": str}``.
        Used by :meth:`stanza_match_question` only — grading in
        :meth:`stanza_match_form` uses :meth:`_stanza_match_prompt_and_correct`
        directly and never needs the distractor set.
        """
        picked = self._stanza_match_pick_translation(stanza)
        prompt, correct = self._stanza_match_prompt_and_correct(stanza, direction, _picked=picked)
        pool = self._stanza_match_distractor_pool(stanza, all_stanzas, direction)

        def _norm(t: str) -> str:
            return " ".join(t.split()).strip().lower()

        if direction == "grc_to_tr":
            # correct is already translator-attributed; dedup and length-
            # bucketing below compare against the pool's still-unattributed
            # candidates, so they need the raw text, not the display form.
            _raw_correct, _correct_translator = (picked[1], picked[0]) if picked else ("", None)
            _correct_norm = _norm(_raw_correct)
            _lo, _hi = len(_raw_correct) * 0.5, len(_raw_correct) * 1.8

            # One distractor per OTHER translator (never the correct answer's
            # own), so every option in the round is attributed to a
            # different translator instead of collapsing onto whichever
            # translator happens to dominate the other stanzas.
            by_translator: "dict[str, list[str]]" = {}
            for _ref, translator, txt in pool:
                if translator == _correct_translator or _norm(txt) == _correct_norm:
                    continue
                by_translator.setdefault(translator, []).append(txt)

            other_translators = list(by_translator)
            rng.shuffle(other_translators)
            distractors = []
            for translator in other_translators[:n_options - 1]:
                cands = by_translator[translator]
                # Length-normalize within this translator's own candidates;
                # fall back to the untrimmed set only if none are comparable.
                bucketed = [c for c in cands if _lo <= len(c) <= _hi] or cands
                distractors.append(self._stanza_match_attribute_option(rng.choice(bucketed), translator))
        else:
            # Options are plain Greek text (translator-agnostic) -- dedup by
            # stanza ref so no two options are drawn from the same stanza.
            _correct_norm = _norm(correct)
            _lo, _hi = len(correct) * 0.5, len(correct) * 1.8
            seen_refs, candidates = set(), []
            for ref, _translator, txt in pool:
                if ref in seen_refs or _norm(txt) == _correct_norm:
                    continue
                seen_refs.add(ref)
                candidates.append(txt)
            bucketed = [c for c in candidates if _lo <= len(c) <= _hi] or candidates
            distractors = rng.sample(bucketed, min(n_options - 1, len(bucketed)))

        options = [correct] + distractors
        rng.shuffle(options)
        return {"prompt": prompt, "options": options, "correct": correct}

    def stanza_match_question(self, stanza: "dict | None", all_stanzas: "list[dict]",
                               direction: str, lang: str, rng: Any, *, n_options: int = 3,
                               initial_value: "str | None" = None) -> tuple:
        """Build a radio-button question for one stanza-match round.

        Returns ``(radio, stanza)``. Calls ``mo.stop`` when *stanza* is
        None so the cell halts cleanly without raising.
        """
        mo = self._mo
        if stanza is None:
            mo.stop(True, mo.md(""))
        round_ = self._stanza_match_round(stanza, all_stanzas, direction, rng, n_options=n_options)
        _kw = {"value": initial_value} if initial_value is not None and initial_value in round_["options"] else {}
        radio = mo.ui.radio(
            options=round_["options"],
            label=f"{round_['prompt']}\n\n{_STANZA_MATCH_LBL.get(lang, {}).get(direction, '')}",
            **_kw,
        )
        return radio, stanza

    def stanza_match_widgets(self, *, cv: "dict | None", remaining: "list | None",
                              stanzas: "list[dict]",
                              direction: str = "grc_to_tr", n_options: int = 3,
                              restore_entry: "dict | None" = None,
                              history_len: int = 0, lang: str = "ru") -> tuple:
        """Create widgets for a stanza↔translation matching exercise.

        Returns ``(choice_radio, next_btn, prev_btn)``. Unpack in a single
        cell so marimo tracks ``choice_radio`` and re-runs the companion
        :meth:`stanza_match_form` cell on selection. ``remaining`` is the
        already-called state value (see :meth:`word_drill_done`) — used only
        alongside ``cv`` to derive whether the exercise is finished, for the
        Next/Prev button labels.
        """
        if cv is None:
            choice_radio = self._mo.ui.radio(options=[""])
        else:
            _restore = restore_entry.get("answer") if restore_entry else None
            choice_radio, _ = self.stanza_match_question(
                cv, stanzas, direction, lang, _random, n_options=n_options, initial_value=_restore,
            )
        _done = self.word_drill_done(cv, remaining)
        next_btn, prev_btn = self._make_nav_buttons(done=_done, history_len=history_len, lang=lang)
        return choice_radio, next_btn, prev_btn

    def stanza_match_form(
        self,
        get_cv, set_cv,
        get_remaining, set_remaining,
        get_score, set_score,
        get_restore, set_restore,
        get_history, set_history,
        get_future, set_future,
        choice_radio: Any,
        next_btn: Any,
        prev_btn: Any,
        *,
        stanzas: "list[dict]",
        direction: str = "grc_to_tr",
        title: str = "",
        lang: str = "ru",
        renew_btn: "Any | None" = None,
    ) -> Any:
        """Standalone stanza↔translation matcher: initialization, navigation, display.

        Companion to :meth:`stanza_match_widgets`. Place in the cell after the
        state and widget cells — mirrors :meth:`word_quiz_form`'s shape, with
        ``stanzas`` standing in for ``vocab`` and a stanza dict standing in
        for a word dict. ``direction`` picks the prompt/answer side:
        ``"grc_to_tr"`` shows the Greek stanza and asks for the matching
        translation; ``"tr_to_grc"`` shows a translation and asks for the
        matching Greek stanza. Grading uses
        :meth:`_stanza_match_prompt_and_correct` — a pure function of the
        current stanza, so it always agrees with the options
        :meth:`stanza_match_widgets` built, without recomputing them.
        ``renew_btn``, if given, renders alongside prev/next (see
        :meth:`word_quiz_form`).
        """
        mo = self._mo
        cv = get_cv()
        remaining = get_remaining()
        score = get_score()
        restore_entry = get_restore()
        history = get_history()
        future = get_future()

        if remaining is None:
            if stanzas:
                self._shuffle_start(stanzas, set_cv, set_remaining)
            return mo.md("*...*")

        _done = cv is None and len(remaining) == 0
        _ans = choice_radio.value
        _correct = self._stanza_match_prompt_and_correct(cv, direction)[1] if cv else None

        if next_btn.value:
            _result = self._handle_quiz_next(
                stanzas, cv, _ans, _correct, remaining, restore_entry, history, future, score,
                set_cv, set_remaining, set_history, set_future, set_score, set_restore, mo,
            )
            if _result is not None:
                return _result
            # else: no selection — fall through and re-render as-is

        if prev_btn.value:
            return self._handle_prev(cv, restore_entry, history, future, score,
                                     set_cv, set_history, set_future, set_score, set_restore, mo)

        if _done:
            self._quiz_done_stop(score, lang, next_btn=next_btn)

        _fb_ans = _ans if _ans is not None else (restore_entry["answer"] if restore_entry else None)
        fb = self._quiz_result_span(mo, _fb_ans, _correct, lang)
        _pfx = f"{title}\n\n" if title else ""
        _corr = _QUIZ_PROGRESS_CORR.get(lang, "correct")
        progress = mo.md(f"{_pfx}**{score['total'] + 1}** / {len(stanzas)} — {_corr}: {score['correct']}")
        return mo.vstack([progress, choice_radio, fb, self._nav_row(prev_btn, next_btn, renew_btn)])

    # ------------------------------------------------------- translation-presence quiz (5b)

    def _read_presence_rows(self, tsv_path: Any) -> "list[list[str]]":
        """Raw ``[lemma, form, stanza_ref, translator, reflected]`` rows from
        *tsv_path*.

        A "#"-prefixed lemma (commented-out / removed-word row) is returned as-is,
        prefix included — callers decide whether to keep or drop it. Missing file
        returns an empty list.
        """
        from pathlib import Path
        path = Path(tsv_path)
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:  # skip header
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            rows.append(parts[:5])
        return rows

    def stanza_word_occurrences(self, form: str, stanzas: "list[dict]") -> "list[str]":
        """Refs of every stanza in *stanzas* where *form* actually occurs as a
        whole word token.

        Ground truth from the poem text itself — word-boundary-safe via
        :func:`norm_grc_surface` (the same normalization the clickable-text
        widget's tokenizer uses), not a substring check. A form used in several
        different stanzas is found in all of them; a form that's merely a
        textual prefix of a longer word (e.g. ``"θεά"`` vs ``"θεάων"``) is not
        mistaken for an occurrence, since both sides are normalized *whole
        tokens*, never compared as substrings.
        """
        key = norm_grc_surface(form)
        refs = []
        for s in stanzas:
            tokens = " ".join(s["lines"]).split()
            if any(norm_grc_surface(t) == key for t in tokens):
                refs.append(s["ref"])
        return refs

    def sync_translation_presence_tsv(self, vocab: "list[dict]", translators: "list[str]",
                                       stanzas: "list[dict]", tsv_path: Any) -> None:
        """UPSERT the per-lesson translation-presence answer key at *tsv_path*.

        One row per (word, stanza it actually occurs in, translator) — a word
        used in several stanzas gets one independently-reviewable row per
        occurrence (see :meth:`stanza_word_occurrences`), not a single row
        covering only wherever a hand-authored position label happened to
        point.

        Never overwrites a teacher's ``reflected`` edit. On (re)run:

        - Existing ``(lemma, form, stanza_ref, translator)`` rows are kept
          exactly as read — same ``reflected`` value, same position.
        - New rows for occurrences not already present are appended with
          ``reflected=""`` (unreviewed starter row).
        - Rows whose word no longer exists in ``vocab``, or whose recorded
          occurrence no longer matches the current poem text, are
          comment-prefixed (``"#lemma"``) rather than deleted, preserving any
          teacher edit; a previously-commented row is un-commented if its
          occurrence reappears.
        - A missing file degenerates to "emit every starter row" — safe to call
          unconditionally when scaffolding a new lesson.
        """
        from pathlib import Path

        rows = self._read_presence_rows(tsv_path)

        def _bare(lemma):
            return lemma[1:] if lemma.startswith("#") else lemma

        # Computed once per distinct form and reused below — stanza_word_occurrences
        # is a pure function of (form, stanzas), so the two vocab passes below would
        # otherwise re-tokenize and re-normalize every stanza twice per word.
        occurrences = {w.get("form", ""): self.stanza_word_occurrences(w.get("form", ""), stanzas)
                       for w in vocab}

        valid_keys = set()
        for w in vocab:
            lemma = w.get("lemma") or w.get("form", "")
            form = w.get("form", "")
            for ref in occurrences[form]:
                valid_keys.add((lemma, form, ref))

        seen, out = set(), []
        for lemma, form, ref, translator, reflected in rows:
            bare = _bare(lemma)
            key = (bare, form, ref, translator)
            seen.add(key)
            in_valid = (bare, form, ref) in valid_keys
            commented = lemma.startswith("#")
            if in_valid and commented:
                out.append([bare, form, ref, translator, reflected])
            elif not in_valid and not commented:
                out.append([f"#{lemma}", form, ref, translator, reflected])
            else:
                out.append([lemma, form, ref, translator, reflected])

        for w in vocab:
            lemma = w.get("lemma") or w.get("form", "")
            form = w.get("form", "")
            for ref in occurrences[form]:
                for translator in translators:
                    key = (lemma, form, ref, translator)
                    if key not in seen:
                        out.append([lemma, form, ref, translator, ""])
                        seen.add(key)

        text = "\t".join(["lemma", "form", "stanza_ref", "translator", "reflected"]) + "\n"
        text += "".join("\t".join(r) + "\n" for r in out)
        Path(tsv_path).write_text(text, encoding="utf-8")

    def read_translation_presence_tsv(self, tsv_path: Any) -> "list[dict]":
        """Load translation_presence.tsv, dropping comment-prefixed (removed-word) rows.

        Returns ``{lemma, form, stanza_ref, translator, reflected}`` dicts,
        unreviewed rows included (``reflected == ""``) — pass through
        :meth:`build_translation_presence_items` to get gradable quiz items.
        """
        rows = self._read_presence_rows(tsv_path)
        return [
            {"lemma": lemma, "form": form, "stanza_ref": ref, "translator": translator,
             "reflected": reflected}
            for lemma, form, ref, translator, reflected in rows
            if not lemma.startswith("#")
        ]

    def build_translation_presence_items(self, presence_rows: "list[dict]", vocab: "list[dict]",
                                          stanzas: "list[dict]") -> "list[dict]":
        """Cross-reference *presence_rows* against *vocab* (for meaning) and
        *stanzas* (the translator's passage text, keyed by each row's own
        ``stanza_ref``) into ready-to-grade items for
        :meth:`translation_presence_form`.

        A row is silently skipped — not an error — if its ``reflected`` hasn't
        been reviewed yet (not ``"yes"``/``"no"``), its word isn't in *vocab*,
        its ``stanza_ref`` doesn't match any stanza, or that translator has no
        real text for that stanza. Mirrors this exercise's existing "missing
        row is tolerated" contract — an unreviewed row has no confident ground
        truth, so it's treated the same as a missing one rather than silently
        graded as "no".
        """
        vocab_by_key = {(w.get("lemma") or w.get("form", ""), w.get("form", "")): w for w in vocab}
        stanzas_by_ref = {s["ref"]: s for s in stanzas}
        items = []
        for row in presence_rows:
            if row.get("reflected") not in ("yes", "no"):
                continue
            w = vocab_by_key.get((row["lemma"], row["form"]))
            if w is None:
                continue
            stanza = stanzas_by_ref.get(row.get("stanza_ref"))
            if stanza is None:
                continue
            passage = stanza.get("translations", {}).get(row["translator"])
            if not passage or passage == "—":
                continue
            items.append({
                "lemma": row["lemma"],
                "form": row["form"],
                "meaning": w.get("meaning", ""),
                "translator": row["translator"],
                "passage": passage,
                "source": "\n".join(stanza["lines"]),
                "reflected": row["reflected"],
            })
        return items

    def balance_presence_items(self, items: "list[dict]", *, no_ratio: float = 0.5,
                                n: "int | None" = 10) -> "list[dict]":
        """Subsample *items* (from :meth:`build_translation_presence_items`) so
        answering "yes" to everything stops being a winning strategy.

        Real translation omissions are rare, so reviewed ``"no"`` items are
        always a small minority of the full set — serving every item every
        session lets a student score ~166/176 (94%) by never reading the
        passage. Keeps *no_ratio* of the session as ``"no"`` items (default
        even split) and randomly samples the rest as ``"yes"``, so the
        session's class split stays close to *no_ratio* instead of whatever
        ratio the reviewed data happens to have.

        *n* caps the total session size (default 10, matching every other
        Odyssey exercise's session cap — see :meth:`sample_session_items`).
        Pass ``n=None`` for the pre-cap behavior: keep *every* ``"no"`` item
        and match it with an equal-or-larger ``"yes"`` sample, size
        determined purely by *no_ratio* and however many ``"no"`` items
        exist. With a numeric *n*, the ``"no"`` side is itself sampled down
        to ``round(n * no_ratio)`` first (via :meth:`sample_session_items`)
        so a small cap can't quietly serve every "no" item while dropping
        the ratio guarantee.

        Returns *items* unchanged if there are no reviewed items of either
        class — nothing to balance against. Order is NOT shuffled here —
        :meth:`translation_presence_form` already shuffles via
        :meth:`_shuffle_start` when a session starts.
        """
        no_items: list[dict] = []
        yes_items: list[dict] = []
        for it in items:
            reflected = it["reflected"]
            if reflected == "no":
                no_items.append(it)
            elif reflected == "yes":
                yes_items.append(it)
        if not no_items or not yes_items:
            return items
        if n is not None:
            no_items = self.sample_session_items(no_items, round(n * no_ratio))
        target_yes = round(len(no_items) * (1 - no_ratio) / no_ratio)
        if n is not None:
            target_yes = min(target_yes, n - len(no_items))
        return no_items + self.sample_session_items(yes_items, target_yes)

    def _presence_passage_md(self, item: dict, show_source: bool, lang: str) -> str:
        """Blockquote + word markdown for one translation-presence round.

        ``show_source`` picks the original Greek stanza (``item["source"]``,
        attributed to a generic "original" label) instead of the translator's
        rendering (``item["passage"]``, attributed to ``item["translator"]``) —
        student toggles this to peek at the source without affecting the
        да/нет answer, which is tracked by a separate widget.
        """
        _meaning = self._get_meaning(item, lang)
        if show_source:
            text = item["source"]
            attribution = _PRESENCE_SOURCE_LBL.get(lang, _PRESENCE_SOURCE_LBL["ru"])
        else:
            text = item["passage"]
            attribution = item["translator"]
        return f"{self._blockquote_cite(text, attribution)}\n\n**{item['form']}** ({_meaning})"

    def translation_presence_question(self, item: "dict | None", lang: str, *,
                                       initial_value: "str | None" = None) -> tuple:
        """Build a да/нет radio for one translation-presence round.

        Returns ``(radio, item)``. Calls ``mo.stop`` when *item* is None so the cell
        halts cleanly without raising. The radio's own label is just the да/нет
        prompt — the passage/word text is rendered separately (see
        :meth:`_presence_passage_md`) so toggling the source/translation switch
        never has to rebuild (and so never risks resetting) this radio.
        """
        mo = self._mo
        if item is None:
            mo.stop(True, mo.md(""))
        yes, no = _YES_NO.get(lang, _YES_NO["ru"])
        _kw = {"value": initial_value} if initial_value in (yes, no) else {}
        radio = mo.ui.radio(
            options=[yes, no], label=_PRESENCE_LBL.get(lang, _PRESENCE_LBL["ru"]), **_kw,
        )
        return radio, item

    def translation_presence_widgets(self, *, cv: "dict | None", remaining: "list | None",
                                      items: "list[dict]",
                                      restore_entry: "dict | None" = None,
                                      history_len: int = 0, lang: str = "ru") -> tuple:
        """Create widgets for the да/нет translation-presence exercise.

        Returns ``(choice_radio, next_btn, prev_btn, source_switch)``. Unpack in
        a single cell so marimo tracks ``choice_radio``/``source_switch`` and
        re-runs the companion :meth:`translation_presence_form` cell on either
        changing. ``source_switch`` is a fresh ``mo.ui.switch(value=False)``
        every round — always starts showing the translation, never the
        original, per this exercise's own design (the student is being asked
        about the *translation*; the source is an optional check). ``remaining``
        is the already-called state value (see :meth:`word_drill_done`) — used
        only alongside ``cv`` to derive whether the exercise is finished, for
        the Next/Prev button labels.
        """
        if cv is None:
            choice_radio = self._mo.ui.radio(options=[""])
        else:
            _restore = restore_entry.get("answer") if restore_entry else None
            choice_radio, _ = self.translation_presence_question(cv, lang, initial_value=_restore)
        _done = self.word_drill_done(cv, remaining)
        next_btn, prev_btn = self._make_nav_buttons(done=_done, history_len=history_len, lang=lang)
        source_switch = self._mo.ui.switch(value=False)
        return choice_radio, next_btn, prev_btn, source_switch

    def translation_presence_form(
        self,
        get_cv, set_cv,
        get_remaining, set_remaining,
        get_score, set_score,
        get_restore, set_restore,
        get_history, set_history,
        get_future, set_future,
        choice_radio: Any,
        next_btn: Any,
        prev_btn: Any,
        source_switch: Any,
        *,
        items: "list[dict]",
        title: str = "",
        lang: str = "ru",
        renew_btn: "Any | None" = None,
    ) -> Any:
        """Standalone да/нет translation-presence quiz: initialization, navigation, display.

        Companion to :meth:`translation_presence_widgets`. Place in the cell after the
        state and widget cells — mirrors :meth:`stanza_match_form`'s shape, with
        ``items`` (from :meth:`build_translation_presence_items`) standing in for
        ``stanzas``. Grades against each item's own ``reflected`` field ("yes"/"no")
        — the teacher-authored answer key, never the vocab gloss or an automatic
        alignment heuristic. ``source_switch`` toggles the passage display between
        the translation and the original Greek (see :meth:`_presence_passage_md`)
        without affecting grading or the да/нет selection. ``renew_btn``, if
        given, renders alongside prev/next (see :meth:`word_quiz_form`).
        """
        mo = self._mo
        cv = get_cv()
        remaining = get_remaining()
        score = get_score()
        restore_entry = get_restore()
        history = get_history()
        future = get_future()

        if remaining is None:
            if not items:
                return mo.md(_PRESENCE_EMPTY.get(lang, _PRESENCE_EMPTY["ru"]))
            self._shuffle_start(items, set_cv, set_remaining)
            return mo.md("*...*")

        _done = cv is None and len(remaining) == 0
        _ans = choice_radio.value
        _yes, _no = _YES_NO.get(lang, _YES_NO["ru"])
        _correct = (_yes if cv["reflected"] == "yes" else _no) if cv else None

        if next_btn.value:
            _result = self._handle_quiz_next(
                items, cv, _ans, _correct, remaining, restore_entry, history, future, score,
                set_cv, set_remaining, set_history, set_future, set_score, set_restore, mo,
            )
            if _result is not None:
                return _result
            # else: no selection — fall through and re-render as-is

        if prev_btn.value:
            return self._handle_prev(cv, restore_entry, history, future, score,
                                     set_cv, set_history, set_future, set_score, set_restore, mo)

        if _done:
            self._quiz_done_stop(score, lang, next_btn=next_btn)

        _fb_ans = _ans if _ans is not None else (restore_entry["answer"] if restore_entry else None)
        fb = self._quiz_result_span(mo, _fb_ans, _correct, lang)
        _pfx = f"{title}\n\n" if title else ""
        _corr = _QUIZ_PROGRESS_CORR.get(lang, "correct")
        progress = mo.md(f"{_pfx}**{score['total'] + 1}** / {len(items)} — {_corr}: {score['correct']}")
        switch_row = mo.hstack(
            [source_switch, mo.md(_PRESENCE_SWITCH_LBL.get(lang, _PRESENCE_SWITCH_LBL["ru"]))],
            justify="start", align="center", gap=1.0,
        )
        passage_md = mo.md(self._presence_passage_md(cv, source_switch.value, lang))
        return mo.vstack([
            progress, switch_row, passage_md, choice_radio, fb,
            self._nav_row(prev_btn, next_btn, renew_btn),
        ])

    # ------------------------------------------------------- write-word quiz

    @staticmethod
    def ensure_file(filename: str, *, nb_dir: Any, remote_base: str, timeout: int = 30) -> Any:
        """Return path to *filename* inside *nb_dir*, downloading from *remote_base* if absent.

        Returns the local path if the file exists or was downloaded successfully.
        Returns None and prints a warning if the file is missing and the remote fetch fails.
        """
        from pathlib import Path
        import urllib.request
        import urllib.parse
        import socket

        local = Path(nb_dir) / filename
        if not local.exists():
            url = f"{remote_base.rstrip('/')}/{urllib.parse.quote(filename)}"
            prev = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            try:
                urllib.request.urlretrieve(url, local)
            except Exception as exc:
                print(
                    f"ensure_file: could not fetch {filename!r} — {exc}\n"
                    f"  local path checked: {local.resolve()}\n"
                    f"  remote URL tried:   {url}"
                )
                return None
            finally:
                socket.setdefaulttimeout(prev)
        return local

    def _resolve_tsv_path(self, filename: str, *, nb_dir: Any, remote_base: "str | None") -> Any:
        """Return a local path for *filename*, fetching from *remote_base* if given.

        Shared by :meth:`load_vocab_tsv` and :meth:`load_inflected_vocab_tsv`
        — both need the identical local-then-remote resolution, differing
        only in how they parse the resolved file.
        """
        if remote_base is None:
            local = _find_local(nb_dir, filename)
            if local is None:
                raise FileNotFoundError(f"{filename} not found locally and no remote_base provided")
        else:
            # ensure_file does its own local-then-remote check in one pass —
            # pre-checking here first would stat the same path twice.
            local = self.ensure_file(filename, nb_dir=nb_dir, remote_base=remote_base)
            if local is None:
                raise FileNotFoundError(f"{filename}: required TSV could not be fetched from remote")
        return local

    def load_vocab_tsv(self, *filenames: str, nb_dir: Any, remote_base: "str | None" = None) -> "list[dict]":
        """Load one or more Word/Translation TSVs and return vocab word dicts.

        Each dict contains ``form`` and ``meaning``. Flat vocabulary has no
        inflection concept, so ``lemma``/``context`` are intentionally omitted
        rather than duplicated from ``form``/``meaning`` — consumers that read
        ``lemma``/``context`` (e.g. :meth:`word_quiz_feedback`,
        ``build_grc_paradigm_table``) fall back to ``form``/``meaning`` when
        absent. See the "form vs. lemma" note on those methods for why the two
        can legitimately differ for inflected-text vocab sources.

        Missing files are downloaded from *remote_base* when provided.
        """
        import pandas as _pd

        dfs = []
        for filename in filenames:
            local = self._resolve_tsv_path(filename, nb_dir=nb_dir, remote_base=remote_base)
            dfs.append(_pd.read_csv(local, sep="\t"))

        _df = _pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
        result = []
        for _, r in _df.iterrows():
            word = str(r.get("Word", "")).strip()
            if not word:
                continue
            meaning = str(r.get("Translation", "")).strip()
            result.append({"form": word, "meaning": meaning})
        return result

    def load_inflected_vocab_tsv(self, *filenames: str, nb_dir: Any, remote_base: "str | None" = None) -> "list[dict]":
        """Load one or more inflected-text vocab TSVs and return word dicts.

        Unlike :meth:`load_vocab_tsv`'s flat ``Word``/``Translation`` columns
        (which need remapping to ``form``/``meaning``), inflected-text vocab
        already provides ``form``, ``lemma``, ``pos``, ``context``, ``meaning``
        directly as its own TSV columns — a word's surface ``form`` can
        genuinely differ from its dictionary ``lemma`` here, so nothing is
        collapsed or synthesized; each row is returned as-is.

        Missing files are downloaded from *remote_base* when provided.
        """
        result = []
        for filename in filenames:
            local = self._resolve_tsv_path(filename, nb_dir=nb_dir, remote_base=remote_base)
            with open(local, encoding="utf-8") as f:
                result.extend(csv.DictReader(f, delimiter="\t"))
        return result

    def word_write_question(self, word: "dict | None", lang: str) -> Any:
        """Return the diacritics_text widget for a write-the-word exercise.

        Calls ``mo.stop`` when *word* is ``None`` so the cell halts cleanly.
        Use a ``None`` guard in the calling cell (like ``word_quiz_question``).
        Falls back to ``mo.ui.text`` when ``anywidget`` is not installed.

        The returned element's ``.enter_pressed`` counter only re-triggers a
        *different* cell if that cell also references the underlying
        anywidget — marimo tracks frontend-driven reactivity through a real
        ``mo.ui.UIElement``, and this wrapper isn't one. If hand-rolling
        (rather than using ``word_drill_widgets``/``word_drill_display``,
        which already expose this as ``dia_reactive``), unpack a second name
        for it — e.g. ``dia = getattr(write_input, "_ui", write_input)`` —
        and reference ``dia`` in whichever cell must react to Enter.
        """
        mo = self._mo
        if word is None:
            mo.stop(True, mo.md(""))
        return diacritics_text(
            mo, placeholder=_WRITE_PLACEHOLDER.get(lang, "Greek word…"),
        )

    def diacritics_text(self, *, placeholder: str = "", label: str = "", value: str = "") -> Any:
        """Combined diacritics bar + text input; wraps :func:`diacritics_text`."""
        return diacritics_text(self._mo, placeholder=placeholder, label=label, value=value)


# ══════════════════════════════ grc paradigm display ══

_GRC_CL   = _FMT_CASE["ru"]
_GRC_NL   = ("Ед.", "Мн.")
_GRC_DL   = "Дв."  # dual column label -- pronoun-only; nouns/adjectives have no dual axis
_GRC_TCOL = {"PAI": "Наст.", "IAI": "Имп.", "AAI": "Аор.", "AMI": "Аор. М.", "API": "Аор. П.", "XAI": "Перф.", "YAI": "Плюскв."}
_GRC_PROW = {"1S": "1 ед.", "2S": "2 ед.", "3S": "3 ед.", "1D": "1 дв.", "2D": "2 дв.", "3D": "3 дв.", "1P": "1 мн.", "2P": "2 мн.", "3P": "3 мн."}
_GRC_INF_LBL = "Инф."
_GRC_IMP_LBL = {"2S": "Пов. 2ед.", "2D": "Пов. 2дв.", "2P": "Пов. 2мн."}
# Tab button label — the historical PERIOD (what the reader sees on the chooser button).
_GRC_LEX_PERIOD = {
    "homer":    "Epic Greek · c. 800–700 BCE",
    "lsj":      "Classical Attic · 5th–4th c. BCE",
    "lxx":      "Hellenistic Koine · late 4th–1st c. BCE",
    "morphgnt": "Roman Koine · 1st–3rd c. CE",
    "modern":   "Modern Greek · 16th c.–present",
    "unimorph": "Koine / NT",
    "byzantine": "Byzantine Greek · 4th–15th c. CE",
}
# Tab caption — the backend/lexicon detail (the secondary "comment" under the buttons).
_GRC_LEX_DESCR = {
    "homer":    "homer lexicon · 2,335 stems · Epic/Ionic",
    "lsj":      "pratt + ltrg + lsj · ~105 stems · Classical Attic",
    "lxx":      "lxx lexicon · 1,905 stems · Septuagint",
    "morphgnt": "morphgnt lexicon · 1,848 stems · NT",
    "modern":   "modern-greek · rule-based (el) · living language",
    "unimorph": "unimorph · 2,224 noun / 207 adj · Wiktionary-derived",
    "byzantine": "byzantine lexicon · 61 stems · hand-curated (Sophocles)",
}
_GRC_CASE_KEY = {"N": "Nom", "G": "Gen", "D": "Dat", "A": "Acc", "V": "Voc"}
_GRC_HL  = "background:#fef3c7;font-weight:bold;color:#92400e;padding:3px 10px;text-align:center;font-family:serif;"
_GRC_TD  = "padding:3px 10px;text-align:center;font-family:serif;"
_GRC_TH  = "padding:3px 8px;font-weight:600;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:.82em;text-align:center;"
_GRC_ROW = "padding:3px 8px;color:#9ca3af;font-size:.82em;text-align:right;"
_GRC_CAP = "font-size:.75em;color:#9ca3af;text-align:left;padding:2px 4px;"
_GRC_NOTE = "background:#fff7ed;border-left:3px solid #f97316;padding:7px 12px;margin-top:8px;font-size:.9em;color:#7c2d12;"


def _norm_grc(s: str) -> str:
    """Strip accents and breathings (but keep iota subscript), lowercase."""
    _STRIP = {"̀", "́", "̂", "̈", "̓", "̔",
              "͂", "̄", "̆"}
    s = _unicodedata.normalize("NFD", s).lower()
    return _unicodedata.normalize("NFC", "".join(c for c in s if c not in _STRIP))


def build_grc_paradigm_table(
    ag_backend: Any,
    um_backend: Any,
    *,
    lang: str = "ru",
) -> Any:
    """Return a ``build_paradigm_table(w)`` closure bound to the given backends.

    Renders an HTML paradigm table for a word dict with ``pos`` (``"noun"`` |
    ``"verb"`` | ``"adj"``) and ``form`` (for highlighting the tested form).
    ``lemma`` is optional — the dictionary form the paradigm is built from;
    falls back to ``form`` when absent (flat vocab). Falls back to the
    UniMorph backend for nouns when the AG backend has no data. Returns
    ``None`` for words with no paradigm data.

    Usage::

        build_paradigm_table = eee.build_grc_paradigm_table(ag_backend, um_backend)
        html = build_paradigm_table(word_dict)
    """
    import functools
    import eee_project as _eee

    @functools.lru_cache(maxsize=None)
    def _ag_slots(pos):
        t = ag_backend.get_slot_templates("grc", pos, lang)
        return {} if t is None else {s.tag: s for s in t}

    @functools.lru_cache(maxsize=None)
    def _um_noun_slots():
        t = um_backend.get_slot_templates("grc", "noun", lang)
        return {} if t is None else {s.tag: s for s in t}

    def build_paradigm_table(
        w: dict, *, lang: "str | None" = None, _backend: Any = None, _cap: "str | None" = None,
        hide_if_absent: bool = False,
    ) -> "str | None":
        """Render the full paradigm for w["lemma"] and highlight w["form"] within it.

        w["lemma"] is the dictionary headword the paradigm is built from;
        w["form"] is the specific (possibly inflected) form being tested
        against it. Falls back to form when lemma is absent (flat vocab, where
        the two are the same word) — see load_vocab_tsv's docstring.
        """
        lemma, pos, tested = _lemma_of(w, w["form"]), w["pos"], w["form"]
        _lex = _backend or ag_backend
        tn = _norm_grc(tested)
        found = False
        any_forms = False
        sg_lbl, pl_lbl = _GRC_NL

        def _td(forms):
            nonlocal found, any_forms
            if forms:
                any_forms = True
            hl = any(_norm_grc(f.replace("(ν)", "ν")) == tn for f in forms)
            if hl:
                found = True
            return (
                f'<td style="{_GRC_HL if hl else _GRC_TD}">'
                f'{"/ ".join(sorted(forms)) if forms else chr(8212)}</td>'
            )

        def _collect_rows(nmap, cases, pos_str, numbers=("S", "P")):
            rows = {}
            for c in cases:
                for n in numbers:
                    forms = set()
                    for g in "MFN":
                        slot = nmap.get(f".{c}{n}{g}")
                        if slot:
                            forms |= _eee.inflect_slot(lemma, slot, pos_str, language="grc", backend=_lex)
                    rows[(c, n)] = forms
            return rows

        def _case_table(caption, cases, ag_rows, numbers=("S", "P"), num_labels=None):
            labels = num_labels or (sg_lbl, pl_lbl)
            assert len(labels) == len(numbers), (
                "numbers and num_labels must be the same length/order -- "
                f"got {numbers!r} vs {labels!r}"
            )
            tbl = (
                f'<table style="border-collapse:collapse;font-size:.95em;margin-top:8px">'
                f'<caption style="{_GRC_CAP}">{caption}</caption>'
                f'<tr><th style="{_GRC_TH}"></th>'
                + "".join(f'<th style="{_GRC_TH}">{lbl}</th>' for lbl in labels) + '</tr>'
            )
            for c in cases:
                tbl += f'<tr><td style="{_GRC_ROW}">{_GRC_CL.get(_GRC_CASE_KEY[c], c)}</td>'
                for n in numbers:
                    tbl += _td(ag_rows[(c, n)])
                tbl += "</tr>"
            return tbl + "</table>"

        if pos == "noun":
            ag_rows = _collect_rows(_ag_slots("noun"), ["N", "G", "D", "A", "V"], "noun")
            _ag_has = any(ag_rows.values())
            be_lbl = (_cap or w.get("lexicon_tag") or "ancient-greek") if _ag_has else "unimorph"
            if _ag_has:
                tbl = _case_table(be_lbl, ["N", "G", "D", "A", "V"], ag_rows)
            else:
                _UM_CASE = {"N": "NOM", "G": "GEN", "D": "DAT", "A": "ACC", "V": "VOC"}
                um_rows = {(c, n): set() for c in ["N", "G", "D", "A", "V"] for n in ("S", "P")}
                if _backend is None:
                    um_nmap = _um_noun_slots()
                    for c in ["N", "G", "D", "A", "V"]:
                        for n, ns in (("S", "SG"), ("P", "PL")):
                            slot = um_nmap.get(f"N;{_UM_CASE[c]};{ns}")
                            um_rows[(c, n)] = (_eee.inflect_slot(lemma, slot, "noun", language="grc", backend=um_backend)
                                                if slot else set())
                tbl = _case_table(be_lbl, ["N", "G", "D", "A", "V"], um_rows)

        elif pos == "verb":
            slot_map = _ag_slots("verb")
            # 2D/3D (dual) only ever populate for the tense/voice combos the
            # stemming engine actually supports (Pres/Imp/Fut/Perf Act Ind +
            # Pres Act Imp) -- Greek has no 1st-person dual, and Aor/Mid/Pass
            # dual have zero rule coverage, so those cells correctly show "—".
            _PS = ["1S", "2S", "3S", "2D", "3D", "1P", "2P", "3P"]
            _vcache = {}

            def _vf(tag):
                if tag not in _vcache:
                    slot = slot_map.get(tag)
                    _vcache[tag] = (_eee.inflect_slot(lemma, slot, "verb", language="grc", backend=_lex)
                                    if slot else set())
                return _vcache[tag]

            tenses = [(t, _GRC_TCOL.get(t, t)) for t in ["PAI", "IAI", "AAI", "AMI", "API", "XAI", "YAI"]
                      if any(_vf(f"{t}.{ps}") for ps in _PS)]
            if not tenses:
                return None
            tbl = (
                f'<table style="border-collapse:collapse;font-size:.95em;margin-top:8px">'
                f'<caption style="{_GRC_CAP}">{_cap or w.get("lexicon_tag") or "ancient-greek"}</caption>'
                f'<tr><th style="{_GRC_TH}"></th>'
            )
            tbl += "".join(f'<th style="{_GRC_TH}">{lbl}</th>' for _, lbl in tenses) + "</tr>"
            for ps in _PS:
                tbl += f'<tr><td style="{_GRC_ROW}">{_GRC_PROW.get(ps, ps)}</td>'
                for t, _ in tenses:
                    tbl += _td(_vf(f"{t}.{ps}"))
                tbl += "</tr>"
            _INF_MAP = {"PAI": "PAN", "IAI": "IAN", "AAI": "AAN", "AMI": "AMN", "API": "APN"}
            if any(_vf(_INF_MAP.get(t, "")) for t, _ in tenses):
                tbl += f'<tr><td style="{_GRC_ROW}">{_GRC_INF_LBL}</td>'
                for t, _ in tenses:
                    tbl += _td(_vf(_INF_MAP.get(t, "")))
                tbl += "</tr>"
            _IMP_MAP = {"PAI": "PAD", "AAI": "AAD", "AMI": "AMD"}
            for imp_ps, imp_sfx in [("2S", ".2S"), ("2D", ".2D"), ("2P", ".2P")]:
                if any(_vf(f"{_IMP_MAP[t]}{imp_sfx}") for t, _ in tenses if t in _IMP_MAP):
                    tbl += f'<tr><td style="{_GRC_ROW}">{_GRC_IMP_LBL.get(imp_ps, imp_ps)}</td>'
                    for t, _ in tenses:
                        imp_t = _IMP_MAP.get(t)
                        tbl += _td(_vf(f"{imp_t}{imp_sfx}")) if imp_t else f'<td style="{_GRC_TD}">—</td>'
                    tbl += "</tr>"
            tbl += "</table>"

        elif pos == "adj":
            ag_rows = _collect_rows(_ag_slots("adjective"), ["N", "G", "D", "A"], "adjective")
            if not any(ag_rows.values()):
                return None
            tbl = _case_table(_cap or w.get("lexicon_tag") or "ancient-greek", ["N", "G", "D", "A"], ag_rows)

        elif pos == "pronoun":
            # _ag_slots("pronoun") returns one flat {tag: slot} dict
            # spanning both pronoun families together (pronoun-tags.tsv
            # holds rows for both shapes in the same file) -- which shape
            # a given lemma needs is decided directly via _PRON_TYPE (the
            # same closed-class lookup resolve_word_grammar already uses
            # for this exact purpose), not inferred from which query
            # happens to come back non-empty.
            if _PRON_TYPE.get(lemma) == "Prs":
                # Personal-pronoun family (ἐγώ/σύ): Case x Number(incl.
                # Dual) x Person grid, no Gender axis at all -- not a
                # reuse of _case_table's caller-side numbers (verb branch
                # has no Tense/Voice/Mood either, a different shape
                # again). Dual columns render unconditionally as part of
                # the grid (same principle as the verb branch's dual
                # rows): individual cells fall back to "—" via _td, but
                # the column itself is never conditionally omitted. This
                # family's dual is 1st/2nd person (νώ/νῷν, σφώ/σφῷν) --
                # no 3rd-person personal pronoun in scope (that's αὐτός,
                # pos="adjective").
                pron_slots = _ag_slots("pronoun")
                _PN_COLS = ["1S", "1D", "1P", "2S", "2D", "2P"]
                pron_rows = {}
                for c in "NGDA":
                    for pn in _PN_COLS:
                        p, n = pn[0], pn[1]
                        slot = pron_slots.get(f".{c}{n}{p}")
                        pron_rows[(c, pn)] = (_eee.inflect_slot(lemma, slot, "pronoun", language="grc", backend=_lex)
                                               if slot else set())
                if not any(pron_rows.values()):
                    return None
                tbl = _case_table(_cap or w.get("lexicon_tag") or "ancient-greek", ["N", "G", "D", "A"], pron_rows,
                                   numbers=_PN_COLS, num_labels=[_GRC_PROW[pn] for pn in _PN_COLS])
            else:
                # Adjective-shaped families (Dem/Rel/Int/Ind/Rcp): same
                # Case+Number+Gender tag composition as regular
                # adjectives. Unlike nouns/adjectives (adj-tags.tsv has
                # zero Dual rows -- _collect_rows/_case_table's default
                # numbers=("S","P") is lossless for them), these
                # genuinely have Dual forms in pronoun-tags.tsv
                # (confirmed: e.g. .NDM/.GDM rows for Dem/Rel/Rcp) --
                # caught in code review after an earlier version of this
                # branch reused the 2-column default and silently made
                # every pronoun dual cell unreachable. numbers=
                # ("S","P","D") below is unconditional (not gated by
                # whether this specific lemma has dual data), matching
                # the verb branch's own dual-row convention.
                ag_rows = _collect_rows(_ag_slots("pronoun"), ["N", "G", "D", "A"], "pronoun", numbers=("S", "P", "D"))
                if not any(ag_rows.values()):
                    return None
                tbl = _case_table(_cap or w.get("lexicon_tag") or "ancient-greek", ["N", "G", "D", "A"], ag_rows,
                                   numbers=("S", "P", "D"), num_labels=(sg_lbl, pl_lbl, _GRC_DL))

        else:
            return None

        if not any_forms:
            return None
        if not found:
            if hide_if_absent:
                return None
            note = f'<div style="{_GRC_NOTE}"><b>{tested}</b> — отсутствует в парадигме {lemma}</div>'
            return note + tbl
        return tbl

    return build_paradigm_table


# ── Modern-Greek (el) diachronic paradigm renderer (parallel to the grc one) ──
_EL_CASES = ["Nom", "Gen", "Acc", "Voc"]        # Modern nouns/adj: 4 cases, no dative
_EL_VERB_COLS = [                               # (column label, base features, particle)
    ("Наст.",    {"Tense": "Pres", "Mood": "Ind"},                  ""),
    ("Имперф.",  {"Tense": "Past", "Aspect": "Imp",  "Mood": "Ind"}, ""),
    ("Аор.",     {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind"}, ""),
    ("Буд.",     {"Tense": "Fut",  "Aspect": "Perf", "Mood": "Ind"}, "θα"),
    ("Буд. дл.", {"Tense": "Fut",  "Aspect": "Imp",  "Mood": "Ind"}, "θα"),
    ("Сосл.",    {"Mood": "Sub",   "Aspect": "Perf"},                "να"),
    ("Повел.",   {"Mood": "Imp",   "Aspect": "Perf"},                ""),
]


def build_modern_paradigm_table(el_backend: Any, *, lang: str = "ru") -> Any:
    """Return a ``build_paradigm_table(w)`` closure rendering a **Modern Greek**
    (``el``) paradigm, parallel to :func:`build_grc_paradigm_table` (left untouched).

    The word's polytonic Ancient ``lemma`` is normalized to monotonic Modern via
    :func:`poly_to_mono` before inflection. Nouns/adjectives show 4 cases
    (Nom/Gen/Acc/Voc — no dative) × sg/pl; verbs show present / imperfect / aorist /
    θα-future (simple + continuous) / να-subjunctive / imperative over 6 persons, in
    separate Active/Passive tables, with the θα/να particle shown **in the form
    cell**. Returns ``None`` when the Modern backend yields no forms (a shifted/dead
    lemma with no Modern reflex → no Modern rung). Shares the grc renderer's HTML
    styles.
    """
    import functools
    import html as _html
    import eee_project as _eee

    @functools.lru_cache(maxsize=None)
    def _el_slots(pos):
        t = el_backend.get_slot_templates("el", pos, lang)
        return {} if t is None else {frozenset(s.features.items()): s for s in t}

    def build_paradigm_table(
        w: dict, *, lang: "str | None" = None, _backend: Any = None,
        _cap: "str | None" = None, hide_if_absent: bool = False,
    ) -> "str | None":
        lemma = poly_to_mono(_lemma_of(w, w["form"]))
        pos = w["pos"]
        tested = strip_diacritics(w["form"]).lower()
        be = _backend or el_backend
        any_forms = False
        sg_lbl, pl_lbl = _GRC_NL

        def _forms(feats, pos_str, particle=""):
            slot = _el_slots(pos_str).get(frozenset(feats.items()))
            if not slot:
                return set()
            fs = _eee.inflect_slot(lemma, slot, pos_str, language="el", backend=be)
            return {f"{particle} {f}" for f in fs} if (particle and fs) else fs

        def _td(forms):
            nonlocal any_forms
            if forms:
                any_forms = True
            hl = any(strip_diacritics(f.split()[-1]).lower() == tested for f in forms)
            cell = "/ ".join(_html.escape(f) for f in sorted(forms)) if forms else chr(8212)
            return f'<td style="{_GRC_HL if hl else _GRC_TD}">{cell}</td>'

        if pos in ("noun", "adjective"):
            rows = {}
            for c in _EL_CASES:
                for nl, n in (("S", "Sing"), ("P", "Plur")):
                    fs = set()
                    for g in ("Masc", "Fem", "Neut"):
                        fs |= _forms({"Case": c, "Number": n, "Gender": g}, pos)
                    rows[(c, nl)] = fs
            if not any(rows.values()):
                return None
            tbl = (
                f'<table style="border-collapse:collapse;font-size:.95em;margin-top:8px">'
                f'<caption style="{_GRC_CAP}">{_html.escape(_cap or "новогреческий")}</caption>'
                f'<tr><th style="{_GRC_TH}"></th>'
                f'<th style="{_GRC_TH}">{sg_lbl}</th><th style="{_GRC_TH}">{pl_lbl}</th></tr>'
            )
            for c in _EL_CASES:
                tbl += f'<tr><td style="{_GRC_ROW}">{_GRC_CL.get(c, c)}</td>'
                tbl += _td(rows[(c, "S")]) + _td(rows[(c, "P")]) + "</tr>"
            result = tbl + "</table>"

        elif pos == "verb":
            _PS = [("1", "Sing", "1S"), ("2", "Sing", "2S"), ("3", "Sing", "3S"),
                   ("1", "Plur", "1P"), ("2", "Plur", "2P"), ("3", "Plur", "3P")]
            tables = []
            for voice, vcap in (("Act", "действ."), ("Pass", "страд.")):
                grid, cols = {}, []
                for clbl, base, part in _EL_VERB_COLS:
                    col, has = {}, False
                    for person, num, ps in _PS:
                        f = _forms({**base, "Voice": voice, "Person": person, "Number": num}, "verb", part)
                        col[ps] = f
                        has = has or bool(f)
                    if has:
                        cols.append(clbl)
                        grid.update({(clbl, ps): col[ps] for ps in col})
                if not cols:
                    continue
                tbl = (
                    f'<table style="border-collapse:collapse;font-size:.95em;margin-top:8px">'
                    f'<caption style="{_GRC_CAP}">{vcap}</caption>'
                    f'<tr><th style="{_GRC_TH}"></th>'
                    + "".join(f'<th style="{_GRC_TH}">{c}</th>' for c in cols) + "</tr>"
                )
                for person, num, ps in _PS:
                    tbl += f'<tr><td style="{_GRC_ROW}">{_GRC_PROW.get(ps, ps)}</td>'
                    tbl += "".join(_td(grid[(c, ps)]) for c in cols) + "</tr>"
                tables.append(tbl + "</table>")
            if not tables:
                return None
            result = "".join(tables)
        else:
            return None

        if hide_if_absent and not any_forms:
            return None
        return result

    return build_paradigm_table


def build_grc_lexicon_tabs(
    ag_backend: Any,
    um_backend: Any,
    *,
    lexicons: "dict[str, Any]",
    el_backend: "Any | None" = None,
    lang: str = "ru",
    require_lexicon: "str | None" = None,
) -> Any:
    """Return a ``build_lexicon_tabs(w)`` closure for multi-lexicon paradigm display.

    *lexicons* maps lexicon name → single-lexicon backend instance, e.g.::

        build_lexicon_tabs = eee.build_grc_lexicon_tabs(
            ag_backend, um_backend,
            lexicons={"homer": ag_homer, "lxx": ag_lxx, "morphgnt": ag_morphgnt},
        )

    The returned closure renders a CSS radio-tab switcher when a word appears in
    multiple lexicons, a single header when it appears in one, and falls back to
    the unimorph paradigm when not found in any AG lexicon.

    When *el_backend* (a ``ModernGreekBackend``) is given, a **Modern** rung is
    appended after the Ancient lexicons, shown only when the Modern backend yields a
    paradigm for the word's (monotonic-normalized) lemma.

    When *require_lexicon* names a key in *lexicons* (e.g. ``"homer"`` for a
    Homer-anchored lesson), the whole table is hidden unless THAT lexicon
    specifically attests the exact form — even if other lexicons (or Modern) do.
    Showing a Classical/Koine/Modern paradigm for a form the anchor corpus itself
    doesn't use would be misleading for a period-specific lesson, not merely
    incomplete. When attested, the anchor lexicon's own rung still renders
    alongside the rest of the diachronic progression as usual. Default ``None``
    preserves prior behaviour for callers with no single anchor lexicon.
    """
    _build_paradigm = build_grc_paradigm_table(ag_backend, um_backend, lang=lang)
    _build_modern = (build_modern_paradigm_table(el_backend, lang=lang)
                     if el_backend is not None else None)

    def _strip_cap(h: str) -> str:
        return _re.sub(r'<caption[^>]*>.*?</caption>', '', h)

    def build_lexicon_tabs(w: dict, *, lang: "str | None" = None) -> "str | None":
        _req_table = None
        if require_lexicon is not None:
            _req_backend = lexicons.get(require_lexicon)
            if _req_backend is None:
                return None
            try:
                _req_table = _build_paradigm(w, _backend=_req_backend, hide_if_absent=True)
            except Exception:
                # isolate a require_lexicon backend hiccup the same way the Modern
                # rung below is isolated -- one bad word/backend must not abort
                # every call through this closure (Gemini R4-style isolation)
                _req_table = None
            if not _req_table:
                return None

        tag = w.get("lexicon_tag", "")
        # require_lexicon's own confirmation (above) is authoritative and already
        # computed -- exclude it here so the loop below never re-derives it (and
        # can never silently disagree with the direct check just because
        # lexicon_tag's string-membership happens not to name it).
        available = [(n, b) for n, b in lexicons.items()
                     if f'"{n}"' in tag and n != require_lexicon]

        _DSTYLE = "font-size:.72em;color:#9ca3af;margin-bottom:5px"
        _HDR_ST = "font-size:.82em;color:#374151;font-weight:600;margin-top:10px;margin-bottom:1px"

        def _wrap_with_header(label, descr_key, raw):
            hdr = f'<div style="{_HDR_ST}">{label}</div>'
            dsc = f'<div style="{_DSTYLE}">{_GRC_LEX_DESCR.get(descr_key, "")}</div>'
            return f"<div>{hdr}{dsc}{_strip_cap(raw)}</div>"

        tables = []
        if _req_table:
            tables.append((require_lexicon, _strip_cap(_req_table)))

        # Keep only lexicons whose paradigm actually contains the tested form — no
        # "form absent" tables (build_paradigm_table returns None when hide_if_absent).
        for name, backend in available:
            tbl = _build_paradigm(w, _backend=backend, hide_if_absent=True)
            if tbl:
                tables.append((name, _strip_cap(tbl)))

        if len(tables) == 0:
            # No curated AG lexicon attests this EXACT form (lexicon_tag can list a
            # lexicon whose LEMMA has some paradigm even when this specific form
            # isn't in it -- see _lexicon_tag's fallback). Try the unimorph
            # fallback. Note this checks the DEFAULT combined ag_backend/um_backend
            # (no _backend= override) and gates on its caption literally containing
            # "unimorph" -- a real, non-unimorph confirmation from a lexicon not
            # named in `tag` would also be missed here, not just a genuine absence;
            # this is a pre-existing imprecision (relocated, not introduced, by
            # this change), not a claim that every other possibility was ruled out.
            raw = _build_paradigm(w, hide_if_absent=True) or ""
            if "unimorph" not in raw:
                return None
            tables.append(("unimorph", _strip_cap(raw)))

        # append the Modern rung last (Epic → … → Roman → Modern), gated by a
        # non-empty Modern paradigm; isolated so a Modern-side failure never breaks
        # the grc dropdown (Gemini R4). Only reached once at least one ancient rung
        # (curated lexicon or unimorph) has already confirmed this exact form.
        if _build_modern is not None:
            try:
                m = _build_modern(w, hide_if_absent=True)
            except Exception:
                m = None
            if m:
                tables.append(("modern", _strip_cap(m)))

        if len(tables) == 1:
            name = tables[0][0]
            return _wrap_with_header(_GRC_LEX_PERIOD.get(name, name), name, tables[0][1])

        names = [n for n, _ in tables]
        uid = abs(hash(w.get("lemma", "") + w.get("form", ""))) % 99999

        # panels, captions, and the summary's current-period label default to hidden;
        # the :checked radio reveals its own (all via the stylesheet, so :checked can override).
        hide = ",".join(f"#lp-{uid}-{n},#ld-{uid}-{n},.dc-{uid}-{n}" for n in names)
        show = "".join(
            f"#lr-{uid}-{n}:checked~#lp-{uid}-{n}{{display:block}}"
            f"#lr-{uid}-{n}:checked~#ld-{uid}-{n}{{display:block}}"
            f"#lr-{uid}-{n}:checked~.ddw-{uid} .dc-{uid}-{n}{{display:inline}}"
            for n in names
        )
        opt_on = "".join(
            f'#lr-{uid}-{n}:checked~.ddw-{uid} label[for="lr-{uid}-{n}"]'
            "{color:#1e3a8a;font-weight:700;background:#dbeafe}"
            for n in names
        )
        # native <details> handles open/close on click — no focus, no JS; drop the default marker
        nomark = (f".ddw-{uid}>summary{{list-style:none}}"
                  f".ddw-{uid}>summary::-webkit-details-marker{{display:none}}")
        style = f"<style>{hide}{{display:none}}{show}{opt_on}{nomark}</style>"

        # hidden radios drive panel + summary state; <label for> switches them (known to work)
        radios = "".join(
            f'<input type="radio" id="lr-{uid}-{n}" name="lg-{uid}"'
            f'{" checked" if i == 0 else ""} style="display:none">'
            for i, n in enumerate(names)
        )

        # <summary> is the collapsed pill; shows the selected period (only :checked span visible)
        cur = "".join(f'<span class="dc-{uid}-{n}">{_GRC_LEX_PERIOD.get(n, n)}</span>' for n in names)
        _SUM = ("display:inline-flex;align-items:center;gap:6px;font-size:.82em;color:#1f2937;"
                "cursor:pointer;padding:3px 11px;border:1px solid #9ca3af;border-radius:5px;"
                "background:#f3f4f6;user-select:none;list-style:none")
        summary = f'<summary style="{_SUM}">{cur}<span style="color:#6b7280">▾</span></summary>'

        # menu shown when <details open>; inline flow (pushes the table down, never hides it)
        _OPT = ("display:block;font-size:.82em;color:#374151;cursor:pointer;"
                "padding:4px 14px;white-space:nowrap")
        opts = "".join(
            f'<label for="lr-{uid}-{n}" style="{_OPT}">{_GRC_LEX_PERIOD.get(n, n)}</label>'
            for n in names
        )
        _MENU = ("margin-top:3px;background:#fff;border:1px solid #d1d5db;border-radius:6px;"
                 "padding:3px 0;box-shadow:0 2px 8px rgba(0,0,0,.10)")
        menu = f'<div style="{_MENU}">{opts}</div>'
        _WRAP = "display:inline-block;margin-top:10px;margin-bottom:2px"
        widget = f'<details class="ddw-{uid}" style="{_WRAP}">{summary}{menu}</details>'

        panels = "".join(f'<div id="lp-{uid}-{n}">{tbl}</div>' for n, tbl in tables)

        _DSTYLE2 = "font-size:.72em;color:#9ca3af;margin-top:1px;margin-bottom:5px"
        descrs = "".join(
            f'<div id="ld-{uid}-{n}" style="{_DSTYLE2}">{_GRC_LEX_DESCR.get(n, "")}</div>'
            for n in names
        )

        return f'<div>{style}{radios}{widget}{descrs}{panels}</div>'

    return build_lexicon_tabs


def norm_grc_surface(s: str) -> str:
    """Normalize a poem surface form for coverage-highlight set membership.

    Strips all combining marks (accents/breathings/iota subscript) and
    trailing elision/clause punctuation — including the middle dot (U+00B7)
    and Greek ano teleia (U+0387), the Greek semicolon-equivalent (e.g.
    "ἔπερσεν·"), found live: without it, a word ending a clause never matched
    its bare vocab form, silently excluding it from both the clickable-text
    coverage set and translation-presence occurrence search. Case-preserving,
    unlike :func:`_norm_grc` (which lowercases for paradigm-table form
    matching) — this compares against poem text tokens, where case is part
    of the match.
    """
    return strip_diacritics(s).strip("',.··᾽᾿ʼ")


def resolve_clicked_word(words_raw: "list[dict]", selected_form: str) -> "dict | None":
    """Map a clicked poem token back to its vocab entry in ``words_raw``.

    ``selected_form`` is a token as reported by :func:`interactive_text`'s
    ``selected_word`` trait — tag- and edge-punctuation-stripped, but with case,
    accent, and breathing marks intact.

    Tries an **exact** match on ``form`` first — the common, collision-free case,
    since curated vocab ``form`` values are hand-authored to agree byte-for-byte
    with how the word appears in the poem. Falls back to
    :func:`norm_grc_surface`-normalized matching (accent/breathing-insensitive)
    only when no exact match exists, e.g. a genuine sentence-position accent
    shift. The fallback is best-effort, not primary: :func:`norm_grc_surface`
    strips breathing marks too, so it CAN collide two distinct words that differ
    only by breathing (confirmed real case: ὅ vs ὁ, οἳ vs οἱ both normalize to
    the same key) — a plain ``{norm_grc_surface(form): w}`` dict is not safe as
    the primary lookup for exactly this reason.

    Returns ``None`` if ``selected_form`` is empty or no match is found.
    """
    if not selected_form:
        return None
    for w in words_raw:
        if w.get("form") == selected_form:
            return w
    key = norm_grc_surface(selected_form)
    for w in words_raw:
        if norm_grc_surface(w.get("form", "")) == key:
            return w
    return None


def _grc_word_passes_filter(w: dict, mode: str, *, build_paradigm_table: Any,
                             lexicons: "dict[str, Any]") -> bool:
    """True if word ``w`` passes the lexicon filter ``mode``.

    When ``mode`` names a lexicon in ``lexicons`` (``"homer"``, ``"attic"``,
    ``"lxx"``, ``"morphgnt"``, …), the tested surface form must actually appear
    in *that* lexicon's paradigm — not merely the lemma, and not merely the
    combined ancient-greek paradigm. Any other ``mode`` (the "current lexicon"
    default): the form is highlighted — not ``#f97316`` irregular/absent — in
    the combined paradigm table.
    """
    backend = lexicons.get(mode)
    if backend is not None:
        # the tested form must actually appear in the selected lexicon's paradigm
        try:
            return build_paradigm_table(w, _backend=backend, hide_if_absent=True) is not None
        except Exception:
            return False
    try:
        result = build_paradigm_table(w)
        if not result:
            return False
        return "#f97316" not in result
    except Exception:
        return False


def filter_grc_quiz_words(words_raw: list, mode: str, *, build_paradigm_table: Any,
                           lexicons: "dict[str, Any]") -> list:
    """Filter ``QUIZ_WORDS_RAW`` to the words quizzable under filter ``mode``.

    ``mode="none"``: no filtering, return every word. Otherwise ``mode`` names
    a lexicon in ``lexicons`` (e.g. ``"homer"``) — see :func:`_grc_word_passes_filter`.

    Was duplicated identically across all 3 Odyssey lesson notebooks (each
    with its own ``_has_displayable_form``/``_in_homer`` pair) before being
    extracted here.
    """
    if mode == "none":
        return list(words_raw)
    return [w for w in words_raw
            if _grc_word_passes_filter(w, mode, build_paradigm_table=build_paradigm_table,
                                        lexicons=lexicons)]


def grc_coverage_words(words_raw: list, mode: "str | None", *, build_paradigm_table: Any,
                        lexicons: "dict[str, Any]") -> set:
    """Return the set of normalized surface forms to highlight in poem text.

    ``mode=None``: highlighting off, empty set. ``mode="none"``: every
    word's surface form (no filtering). Otherwise ``mode`` names a lexicon in
    ``lexicons`` (e.g. ``"homer"``) — see :func:`_grc_word_passes_filter`.

    Was duplicated identically across all 3 Odyssey lesson notebooks (each
    with its own ``_words_for_coverage``/``_norm_f`` pair) before being
    extracted here.
    """
    if mode is None:
        return set()
    if mode == "none":
        return {norm_grc_surface(w["form"]) for w in words_raw}
    return {norm_grc_surface(w["form"]) for w in words_raw
            if _grc_word_passes_filter(w, mode, build_paradigm_table=build_paradigm_table,
                                        lexicons=lexicons)}


def grc_lexicon_sources(w: dict, *, lexicons: "dict[str, Any]") -> list:
    """Return the sorted names of ``lexicons`` whose full paradigm for
    ``w["lemma"]``/``w["pos"]`` contains ``w["form"]``.

    Comparison is case-folded and accent/breathing-insensitive (movable-nu
    parenthesization normalized too) — real running text varies a lemma's
    citation-form spelling this way constantly (sentence-initial capitals,
    grave-for-acute accent shifts in connected speech, enclitic-driven accent
    shifts elsewhere), none of which are a different word.

    Deliberately does NOT reuse :func:`_grc_word_passes_filter`/
    :func:`build_grc_paradigm_table`: those check only the paradigm cells the
    compact study-table renders, which never include participles — fine for
    that table's own purpose, but would silently drop the lexicon-confirmed
    badge from any word whose only attestation is a participle form (common
    in Homer). This checks the complete ``backend.paradigm()`` result instead.

    Only meaningful for POS values in ``LEXICON_TAG_POS``; returns ``[]`` for
    any other POS.

    Was duplicated identically across all 7 Odyssey lesson notebooks (each
    with its own ``_lexicon_tag`` plus a hand-maintained ``_LEXICONS`` list —
    the same ``(name, backend)`` pairs ``lexicons`` already holds, and an
    exact-string match blind to the surface variation described above)
    before being extracted here.
    """
    if w.get("pos") not in LEXICON_TAG_POS:
        return []
    pos = LEXICON_TAG_POS_ALIASES.get(w["pos"], w["pos"])
    tform = _norm_grc(w.get("form", "").replace("(ν)", "ν"))
    sources = []
    for name, backend in lexicons.items():
        try:
            para = backend.paradigm(w["lemma"], pos)
            if any(_norm_grc(f.replace("(ν)", "ν")) == tform for forms in para.values() for f in forms):
                sources.append(name)
        except Exception:
            pass
    return sorted(sources)
