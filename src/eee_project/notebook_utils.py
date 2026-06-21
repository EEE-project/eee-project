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

    # single-input slot drill (one question at a time, state-machine style)
    # handler cell:
    gu.slot_drill_advance(next_btn.value, write_input.value.strip(),
        cv(), remaining(), field_idx(), score(),
        FIELDS, ALL_ITEMS, random, set_cv, set_remaining, set_field_idx, set_score)
    # display cell:
    gu.slot_drill_display(cv(), field_idx(), score(), write_input, check_btn, next_btn,
        fields=FIELDS, title="## Exercise", n_items=len(ALL_ITEMS))

    # vocab quiz (multiple-choice)
    radio, word = gu.word_quiz_question(cv(), all_words, "ru", random)
    fb = gu.word_quiz_feedback(radio, word, score, "ru")

    # vocab quiz (write the word)
    path = gu.ensure_file("words.tsv", nb_dir=Path(__file__).parent, remote_base=REMOTE_URL)
    words = gu.load_vocab_tsv("verbs.tsv", "nouns.tsv", nb_dir=Path(__file__).parent, remote_base=REMOTE_URL)
    inp, word = gu.word_write_question(cv(), "ru")
    fb = gu.word_write_feedback(inp, word, score, "ru")
"""

from __future__ import annotations

import io
import unicodedata as _unicodedata
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from eee_project._grammar_fmt import fmt_ud_feats
from eee_project._slot_template import SlotTemplate


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
</style>"""

_BADGE = '<a class="tb-badge" href="https://t.me/+VuocC5la3ZwyNDky" target="_blank">EEE Community</a>'

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
    "ru": "🎉 Все слова пройдены! Нажмите «→ Следующее» для повтора.",
    "en": "🎉 All words done! Press «→ Next» to repeat.",
    "el": "🎉 Όλες οι λέξεις! Πατήστε «→ Επόμενο» για επανάληψη.",
}
_QUIZ_CORR  = {"ru": "Верно:", "en": "Correct:", "el": "Σωστά:"}
_QUIZ_POS   = {
    "ru": {"noun": "сущ.", "verb": "глаг.", "adj": "прил.", "adv": "нар."},
    "en": {"noun": "n.",   "verb": "v.",    "adj": "adj.",  "adv": "adv."},
    "el": {"noun": "ουσ.", "verb": "ρ.",    "adj": "επίθ.", "adv": "επίρρ."},
}
_QUIZ_RIGHT = {"ru": "✓ Верно!", "en": "✓ Correct!", "el": "✓ Σωστό!"}
_QUIZ_WRONG = {"ru": "✗ Нет. Правильно:", "en": "✗ No. Correct form:", "el": "✗ Όχι. Σωστή μορφή:"}
_WRITE_PLACEHOLDER = {"ru": "греческое слово…", "en": "Greek word…", "el": "ελληνική λέξη…"}


def _ga_script(measurement_id: str) -> str:
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>'
        f'<script>window.dataLayer=window.dataLayer||[];'
        f'function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());'
        f'gtag("config","{measurement_id}");</script>'
    )


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


class ConfigStore:
    """Navigation and GA config storage with pluggable backends.

    Use :meth:`from_url`, :meth:`from_file`, or :meth:`from_dict` to
    create an instance, then call :meth:`lessons`, :meth:`index_url`, and
    :meth:`ga_config` wherever a notebook needs config — the API is identical
    regardless of storage backend.

    TSV columns: ``nb_id, icon, greek, label, title, desc, index_url``.

    Example — molab (fetch TSV and GA config from Codeberg)::

        _ROOT = "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main"
        _cfg = ConfigStore.from_url(
            f"{_ROOT}/palaestra/lessons.tsv",
            ga=f"{_ROOT}/ga.json",
        )
        eee_topbar(mo, back_url=_cfg.index_url(), ...)

    Example — local dev (files next to the notebook)::

        _cfg = ConfigStore.from_file(__file__)  # reads lessons.tsv + ga.json
    """

    _COLS = ("nb_id", "icon", "greek", "label", "title", "desc", "index_url")

    def __init__(self, lessons: "list[dict]", ga: "dict | None" = None, *,
                 _raw_base: "str | None" = None):
        self._lessons = lessons
        self._ga = ga or {}
        self._raw_base = _raw_base

    @classmethod
    def _parse_tsv(cls, text: str) -> "list[dict]":
        import csv as _csv
        import io as _io
        return [
            {c: row.get(c, "") for c in cls._COLS}
            for row in _csv.DictReader(_io.StringIO(text), delimiter="\t")
        ]

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

        def _find(name):
            for p in (base / name, base.parent / name):
                if p.exists():
                    return p
            return None

        tsv = _find("lessons.tsv")
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

        _raw_base = url.rsplit("/", 1)[0]
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


def eee_topbar(mo, back_url: str, lang: str, titles: "dict | str", *, style: str = "back", icon: str = "●", ga_config=None):
    """Render the EEE sticky navigation topbar.

    Must be the **last expression** in a marimo cell — no trailing ``return``.

    Args:
        mo:        The marimo module (passed from the cell's imports).
        back_url:  URL for the left-side link. Pass ``None`` or ``""`` to
                   suppress the link — in ``style="back"`` this hides the
                   whole bar (except GA); in ``style="index"`` the icon and
                   title still render, just as plain (non-link) text.
        lang:      Current language code (e.g. ``"ru"``, ``"el"``, ``"en"``).
        titles:    Page name as a ``{lang: name}`` dict or a plain string.
        style:     ``"back"`` (default) renders "◀ {title}" linking to
                   ``back_url`` — for content pages one level below an index.
                   ``"index"`` renders "{icon} {title}" instead — for index
                   / landing pages. Linked to ``back_url`` when given (an
                   index that points up to a parent index), plain text when
                   not (a top-level index, or one scoped only to its own
                   level).
        icon:      Glyph shown before the title in ``style="index"``.
        ga_config: Dict from :func:`load_ga_config`, or ``None`` to skip GA.

    Example cell::

        from eee_project.notebook_utils import eee_topbar, load_ga_config
        _ga = load_ga_config(__file__)
        _TITLES = {"ru": "Каподистриас", "el": "Καποδίστριας", "en": "Kapodistrias"}
        eee_topbar(mo, back_url="https://molab.marimo.io/...", lang=lang_sel.value,
                   titles=_TITLES, ga_config=_ga)

        # index/landing page, linking up to a parent index:
        eee_topbar(mo, back_url="https://.../created_with_eee/", lang=lang_sel.value,
                   titles="Kapodistrias", style="index")
    """
    ga_html = _ga_script(ga_config["measurement_id"]) if ga_config and ga_config.get("measurement_id") else ""
    title = titles.get(lang, next(iter(titles.values()))) if isinstance(titles, dict) else titles
    if style == "index":
        left = (f'<a class="tb-back" href="{back_url}" target="_blank">{icon} {title}</a>'
                if back_url else f'<span class="tb-back">{icon} {title}</span>')
    elif not back_url:
        return mo.Html(ga_html) if ga_html else None
    else:
        left = f'<a class="tb-back" href="{back_url}" target="_blank">◀ {title}</a>'
    return mo.Html(f"""{ga_html}{_TOPBAR_CSS}
<div id="eee-topbar">
  {left}
  {_BADGE}
</div>""")


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


# ════════════════════════════════════════ polytonic diacritics bar ══

try:
    import anywidget as _anywidget
    import traitlets as _traitlets
    _ANYWIDGET_OK = True
except ImportError:
    _ANYWIDGET_OK = False


_DIA_CSS = """\
.eee-dia-bar{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0 4px;align-items:center}
.eee-dia-bar .dia-lbl{font-size:12px;color:#555;margin-right:4px;font-family:sans-serif}
.eee-dia-bar button{min-width:52px;min-height:50px;padding:2px 8px;border:1px solid #bbb;
  border-radius:8px;background:#fafafa;cursor:pointer;line-height:1.1;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  touch-action:manipulation;-webkit-tap-highlight-color:transparent;
  font-family:'GFS Didot','New Athena Unicode','Noto Serif',serif}
.eee-dia-bar button:active{background:#e8f4ff;border-color:#003d82}
.eee-dia-bar button.dia-active{background:#dceeff;border-color:#003d82;box-shadow:inset 0 2px 4px rgba(0,61,130,0.2)}
.eee-dia-bar .dia-ch{font-size:26px}
.eee-dia-bar .dia-sub{font-size:9px;color:#555;font-family:sans-serif;margin-top:1px}
.eee-dia-bar .dia-clr{background:#fff5f5;border-color:#ffcdd2;font-family:sans-serif}
.eee-dia-bar .dia-clr .dia-ch{font-size:18px}
.eee-dia-bar .dia-clr:active{background:#ffcdd2}
.eee-dia-inp{width:100%;box-sizing:border-box;padding:6px 8px;font-size:16px;
  border:1px solid #ccc;border-radius:4px;margin-top:2px;
  font-family:'GFS Didot','New Athena Unicode','Noto Serif',serif}
"""

# The input lives INSIDE the widget so beforeinput fires without crossing
# the marimo-text shadow DOM boundary.
# EEE_PLACEHOLDER and EEE_LABEL are replaced at runtime by _make_dia_esm().
# Only `value` is synced so mo.ui.anywidget().value returns a plain string.
_DIA_ESM_TMPL = """\
const MARKS = [
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

function render({ model, el }) {
  const activeMarks = new Map(); // cat → {dia, btn}
  let biSnapshot = null;         // {value, pos} saved in beforeinput for Android fix

  function clear(...cats) {
    for (const cat of cats) {
      const m = activeMarks.get(cat);
      if (m) { m.btn.classList.remove('dia-active'); activeMarks.delete(cat); }
    }
  }

  function clearAll() {
    for (const {btn} of activeMarks.values()) btn.classList.remove('dia-active');
    activeMarks.clear();
  }

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

  for (const {ch, dia, label, cat} of MARKS) {
    const btn = document.createElement('button');
    btn.innerHTML = `<span class="dia-ch">${ch}</span><span class="dia-sub">${label}</span>`;
    btn.addEventListener('mousedown', e => e.preventDefault());
    btn.addEventListener('click', () => {
      const cur = activeMarks.get(cat);
      if (cur && cur.dia === dia) {
        clear(cat);
      } else {
        clear(...(EXCL[cat] || [cat]));
        activeMarks.set(cat, {dia, btn});
        btn.classList.add('dia-active');
      }
      inp.focus();
    });
    bar.appendChild(btn);
  }

  const clr = document.createElement('button');
  clr.className = 'dia-clr';
  clr.innerHTML = '<span class="dia-ch">✕</span><span class="dia-sub">clear</span>';
  clr.addEventListener('mousedown', e => e.preventDefault());
  clr.addEventListener('click', () => {
    clearAll();
    const pos = inp.selectionStart ?? inp.value.length;
    if (pos === 0) { inp.focus(); return; }
    const chars = Array.from(inp.value.slice(0, pos));
    const last = chars.pop();
    const stripped = last.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').normalize('NFC');
    const bstr = chars.join('');
    inp.value = bstr + stripped + inp.value.slice(pos);
    model.set('value', inp.value);
    model.save_changes();
    inp.setSelectionRange(bstr.length + stripped.length, bstr.length + stripped.length);
    inp.focus();
  });
  bar.appendChild(clr);

  const VOWELS      = new Set('αεηιουωΑΕΗΙΟΥΩ');
  const LONG_VOWELS = new Set('αηιυωΑΗΙΥΩ');
  const IOTSUB_V    = new Set('αηωΑΗΩ');
  const DIAER_V     = new Set('ιυΙΥ');
  const DIA_VOWELS  = {
    '\\u0342': LONG_VOWELS,
    '\\u0345': IOTSUB_V,
    '\\u0308': DIAER_V,
  };

  function getMarksFor(base) {
    const m = [...activeMarks.entries()]
      .sort(([a], [b]) => (CAT_ORDER[a] ?? 9) - (CAT_ORDER[b] ?? 9))
      .filter(([, {dia}]) => { const s = DIA_VOWELS[dia]; return !s || s.has(base); })
      .map(([, {dia}]) => dia).join('');
    return m || null;
  }

  inp.addEventListener('beforeinput', e => {
    biSnapshot = null;
    if (!activeMarks.size || !e.data) return;
    const base = e.data.normalize('NFD')[0];
    if (!VOWELS.has(base)) { clearAll(); return; }
    const marks = getMarksFor(base);
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

  el.appendChild(bar);
  el.appendChild(inp);
}
export default { render };
"""


def _make_dia_esm(placeholder: str, label: str) -> str:
    import json as _json
    return (_DIA_ESM_TMPL
            .replace("EEE_PLACEHOLDER", _json.dumps(placeholder))
            .replace("EEE_LABEL", _json.dumps(label)))


def _make_dia_widget_class(placeholder: str, label: str):
    return type("_DiacriticsTextWidget", (_anywidget.AnyWidget,), {
        "_css": _DIA_CSS,
        "_esm": _make_dia_esm(placeholder, label),
        "value": _traitlets.Unicode("").tag(sync=True),
    })


class _DiacriticsElement:
    """Thin wrapper: exposes .value as a plain string; display forwards to widget."""

    def __init__(self, ui_widget: Any) -> None:
        self._ui = ui_widget

    @property
    def value(self) -> str:
        v = self._ui.value
        return v.get("value", "") if isinstance(v, dict) else str(v)

    def _mime_(self) -> Any:
        return self._ui._mime_()


def diacritics_text(mo, *, placeholder: str = "", label: str = "") -> Any:
    """Combined polytonic diacritics bar + text input widget.

    Returns an element whose ``.value`` is the typed text as a plain string
    (drop-in for ``mo.ui.text().value``).
    Buttons stay highlighted until pressed again (persistent diacritic mode).
    Requires ``anywidget``.
    """
    if not _ANYWIDGET_OK:
        return mo.ui.text(placeholder=placeholder or "Greek word…", full_width=True)
    cls = _make_dia_widget_class(placeholder, label)
    return _DiacriticsElement(mo.ui.anywidget(cls()))


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
    tense_labels: dict                  # tense_key → {"greek": ..., "dropdown": ...}
    path_map: dict                      # tense_key → paradigm() key (backend fallback)
    verb_prefix: dict                   # tense_key → particle string (e.g. "θα")
    verb_slots: "list[tuple[str,str]]"  # (num, person) slots per verb exercise
    verb_labels: "list[str]"            # display label per verb slot
    adj_cases: "list[str]"              # cases for full adjective paradigm
    compare_diacritics: bool            # default diacritics flag for _ci


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
        'sg': {'nom': {'ὁ'},  'acc': {'τόν'}, 'gen': {'τοῦ'}, 'dat': {'τῷ'}},
        'pl': {'nom': {'οἱ'}, 'acc': {'τούς'}, 'gen': {'τῶν'}, 'dat': {'τοῖς'}},
    },
    'fem': {
        'sg': {'nom': {'ἡ'},  'acc': {'τήν'}, 'gen': {'τῆς'}, 'dat': {'τῇ'}},
        'pl': {'nom': {'αἱ'}, 'acc': {'τάς'}, 'gen': {'τῶν'}, 'dat': {'ταῖς'}},
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
    tense_labels={
        'present':           {'greek': 'Ενεστώτας',         'dropdown': 'Present (Ενεστώτας)'},
        'imperfect':         {'greek': 'Παρατατικός',       'dropdown': 'Imperfect (Παρατατικός)'},
        'aorist':            {'greek': 'Αόριστος',          'dropdown': 'Aorist (Αόριστος)'},
        'future':            {'greek': 'Απλός Μέλλοντας',   'dropdown': 'Simple Future (Μέλλοντας)'},
        'future_continuous': {'greek': 'Συνεχής Μέλλοντας', 'dropdown': 'Continuous Future (Μέλλοντας)'},
    },
    path_map=_MG_PATH_MAP,
    verb_prefix={'future': 'θα', 'future_continuous': 'θα'},
    verb_slots=_VERB_SLOTS,
    verb_labels=['εγώ', 'εσύ', 'αυτός,-ή,-ό', 'εμείς', 'εσείς', 'αυτοί,-ές,-ά'],
    adj_cases=['nom', 'acc', 'gen'],
    compare_diacritics=True,
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
    tense_labels={
        'present':   {'greek': 'Ἐνεστώς',      'dropdown': 'Present (Ἐνεστώς)'},
        'imperfect': {'greek': 'Παρατατικός',   'dropdown': 'Imperfect (Παρατατικός)'},
        'aorist':    {'greek': 'Ἀόριστος',     'dropdown': 'Aorist (Ἀόριστος)'},
        'perfect':   {'greek': 'Παρακείμενος',  'dropdown': 'Perfect (Παρακείμενος)'},
        'future':    {'greek': 'Μέλλων',        'dropdown': 'Future (Μέλλων)'},
    },
    path_map={},
    verb_prefix={},
    verb_slots=_VERB_SLOTS,
    verb_labels=['1 sg', '2 sg', '3 sg', '1 pl', '2 pl', '3 pl'],
    adj_cases=['nom', 'acc', 'gen', 'dat'],
    compare_diacritics=False,
)


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

    @property
    def TENSE_LABELS(self) -> dict:
        return self._cfg.tense_labels

    # ------------------------------------------------------------------ utils

    def _paradigm(self, word: str, pos: str) -> dict:
        try:
            return self._mg.paradigm(word, pos)
        except Exception:
            return {}

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
        """Inflect via eee.inflect_slot(); None when no eee module was provided."""
        if self._eee is None:
            return None
        slot = SlotTemplate(tag_type="ud", label="", features=features)
        try:
            return self._eee.inflect_slot(word, slot, pos, language=self._cfg.language)
        except Exception:
            return set()

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

    # ------------------------------------------------------------------ nouns

    def create_noun_test_ui(self, words_list, mode='simple'):
        mo = self._mo
        word = translation = noun_form = None
        if words_list and words_list[0]:
            entry = words_list[0]
            word = entry['Word'] if isinstance(entry, dict) else entry
            translation = entry.get('Translation', '') if isinstance(entry, dict) else ''
            parts = word.split()
            nw = parts[1].strip() if len(parts) > 1 else word.strip()
            na = parts[0].strip() if len(parts) > 1 else None
            noun_cells = self._cfg.noun_cells
            pl_cells = [c for c in noun_cells if c[0] == 'pl']
            is_pt = (
                (na is not None and na in self._plural_articles()) or
                not bool(self._noun_forms(nw, 'sg', 'nom'))
            )
            active_cases = (
                pl_cells if is_pt else
                [c for c in noun_cells if bool(self._noun_forms(nw, c[0], c[1]))] or noun_cells
            )
            indef_cells = (
                [c for c in active_cases if c[0] == 'sg']
                if self._cfg.indef_articles else []
            )
            if mode == 'simple':
                labels = [f"{_QUIZ_NUM_LABEL.get(n, n)} {_QUIZ_CASE_LABEL.get(c, c)}:" for n, c in active_cases]
            else:
                labels = (
                    [f"Def. {_QUIZ_NUM_LABEL.get(n, n)} {_QUIZ_CASE_LABEL.get(c, c)}:" for n, c in active_cases] +
                    [f"Ind. {_QUIZ_NUM_LABEL.get(n, n)} {_QUIZ_CASE_LABEL.get(c, c)}:" for n, c in indef_cells]
                )
            noun_form = mo.ui.array([mo.ui.text(label=l) for l in labels])
            noun_form.test_word = word
            noun_form.is_pluralia_tantum = is_pt
            noun_form.active_cases = active_cases
        return word, translation, noun_form

    def check_noun_test(self, noun, noun_form, mode='simple'):
        if not noun or noun_form is None or not noun_form.value:
            return False
        if hasattr(noun_form, 'test_word') and noun_form.test_word != noun:
            return False
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
        _gender_cache: dict = {}

        def _genders_at(num, case):
            key = (num, case)
            if key not in _gender_cache:
                _gender_cache[key] = [g for g in ('masc', 'fem', 'neut')
                                       if self._noun_forms_gender(nw, num, case, g)]
            return _gender_cache[key]

        def _chk(val, num, case, art_table=None, require_art=True):
            if not val:
                return False
            ws = val.split()
            uw, ua = ws[-1].strip(), (ws[0].strip() if len(ws) > 1 else None)
            correct = self._noun_forms(nw, num, case)
            correct_arts: set = set()
            if art_table is not None:
                for g in _genders_at(num, case):
                    correct_arts.update(art_table.get(g, {}).get(num, {}).get(case, set()))
            _n = _QUIZ_NUM_LABEL.get(num, num)
            _c = _QUIZ_CASE_LABEL.get(case, case)
            ok = True
            if not self._ci(uw, correct):
                print(f'❌ [{_n} {_c}]: noun **"{uw}"**, must be **{" / ".join(sorted(correct)) if correct else "?"}**<br>')
                ok = False
            if art_table is not None:
                if ua is None:
                    if require_art:
                        print(f'❌ [{_n} {_c}]: article missing, must be **{" / ".join(sorted(correct_arts))}**<br>')
                        ok = False
                elif not self._ci(ua, correct_arts):
                    print(f'❌ [{_n} {_c}]: article **"{ua}"**, must be **{" / ".join(sorted(correct_arts))}**<br>')
                    ok = False
            return ok

        if mode == 'simple':
            return all([_chk(v, c[0], c[1], arts, require_art=False) for v, c in zip(noun_form.value, ac)])
        else:
            indef_cells = [c for c in ac if c[0] == 'sg'] if indef_arts else []
            def_res  = [_chk(v, c[0], c[1], arts) for v, c in zip(noun_form.value, ac)]
            indef_res = [_chk(v, c[0], c[1], indef_arts)
                         for v, c in zip(noun_form.value[len(ac):], indef_cells)]
            return all(def_res + indef_res)

    # ------------------------------------------------------------------ verbs

    def create_verb_test_ui(self, title, words, words4test_val, current_verb):
        mo = self._mo
        form = None
        md_view = mo.md(f'**The word list for {title} is empty.**')
        if current_verb:
            word = current_verb['Word']
            translation = current_verb['Translation']
            form = mo.ui.array([mo.ui.text(label=f"{lbl}:") for lbl in self._cfg.verb_labels])
            form.verb_word = word
            if words4test_val:
                md_view = mo.md(f"""
### {title}
(words: {len(words4test_val)}/{len(words)})
Translation: **{translation}**
{form}
""")
        return form, md_view

    def check_verb_test(self, verb_base, form_array, tense):
        if form_array is None or not form_array.value:
            return False, ""
        if hasattr(form_array, 'verb_word') and form_array.verb_word != verb_base:
            return False, ""
        if tense not in self._cfg.tense_feats:
            return False, f"Unknown tense '{tense}'"
        pref = self._cfg.verb_prefix.get(tense, '')
        ok, errs = True, []
        for i, ((n, per), lbl) in enumerate(zip(self._cfg.verb_slots, self._cfg.verb_labels)):
            uv = form_array.value[i].strip()
            if not uv:
                ok = False
                continue
            cv = uv
            if pref:
                if uv.lower().startswith(pref):
                    cv = uv[len(pref):].strip()
                else:
                    errs.append(f'❌ [{lbl}]: Write with **"{pref}"**')
                    ok = False
                    continue
            correct = self._verb_forms(verb_base, tense, per, n)
            if not correct or not self._ci(cv, correct):
                ok = False
                exp = '/'.join(correct) if correct else 'unknown'
                if pref:
                    exp = f"{pref} {exp}"
                errs.append(f'❌ [{lbl}]: entered **"{uv}"**, must be **{exp}**')
        return ok, '<br>'.join(errs)

    # --------------------------------------------------------------- adjectives

    def create_adjective_test_ui(self, words, words4test_val, current_adj, mode='simple'):
        mo = self._mo
        form = None
        md_view = mo.md('**The word list for adjective test is empty.**')
        if current_adj:
            word = current_adj['Word']
            translation = current_adj['Translation']
            cm = {c: c.title() for c in self._cfg.adj_cases}
            if mode == 'simple':
                labels = (
                    [f"{_QUIZ_ADJ_GENDER[g]} Sg:" for g in ('masc', 'fem', 'neut')] +
                    [f"{_QUIZ_ADJ_GENDER[g]} Pl:" for g in ('masc', 'fem', 'neut')]
                )
            else:
                labels = [
                    f"{_QUIZ_ADJ_GENDER[g]} {_QUIZ_ADJ_NUM[n]} {cm.get(c, c)}:"
                    for n in ('sg', 'pl') for g in ('masc', 'fem', 'neut')
                    for c in self._cfg.adj_cases
                ]
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

    def check_adjective_test(self, adj_base, form_array, mode='simple'):
        if form_array is None or not form_array.value:
            return False, ""
        if hasattr(form_array, 'adj_word') and form_array.adj_word != adj_base:
            return False, ""
        if hasattr(form_array, 'adj_mode'):
            mode = form_array.adj_mode
        cm = {c: c.title() for c in self._cfg.adj_cases}
        if mode == 'simple':
            fk = ([(g, 'sg', 'nom') for g in ('masc', 'fem', 'neut')] +
                  [(g, 'pl', 'nom') for g in ('masc', 'fem', 'neut')])
            fl = [f"{_QUIZ_ADJ_GENDER[g]} {_QUIZ_ADJ_NUM[n]}" for g, n, c in fk]
        else:
            fk = [(g, n, c) for n in ('sg', 'pl')
                  for g in ('masc', 'fem', 'neut') for c in self._cfg.adj_cases]
            fl = [f"{_QUIZ_ADJ_GENDER[g]} {_QUIZ_ADJ_NUM[n]} {cm.get(c, c)}" for g, n, c in fk]
        ok, has, errs = True, False, []
        for i, ((g, n, c), label) in enumerate(zip(fk, fl)):
            uv = form_array.value[i].strip()
            if not uv:
                ok = False
                continue
            has = True
            correct = self._adj_forms(adj_base, n, g, c) or {adj_base}
            if not self._ci(uv, correct):
                ok = False
                errs.append(f'❌ [{label}]: entered **"{uv}"**, must be **{"/".join(sorted(correct))}**')
        if not has:
            return False, '❌ Please fill in at least one gender form'
        return ok, '<br>'.join(errs)

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
        strict: bool = False,
    ) -> list:
        """Check student answers for a drill created by :meth:`make_item_drill_rows`.

        Args:
            items:        Same list passed to :meth:`make_item_drill_rows`.
            inputs_2d:    Return value from :meth:`make_item_drill_rows`.
            fields:       Same list passed to :meth:`make_item_drill_rows`.
            meaning_key:  Key used for the item label in feedback.
            field_labels: Human-readable label for each field (defaults to field key).
            strict:       Pass ``True`` to require diacritics to match exactly.

        Returns a list of ``mo.md(...)`` feedback elements — one per item that
        has at least one non-empty input.  Feed the list to ``mo.vstack``.

        Example result cell::

            _fb = gu.check_item_drill(
                VERBS, verb_inputs_v, ["verb", "sg", "pl"],
                field_labels=["verb", "sg.", "pl."],
                strict=strict_v.value,
            ) if submit_btn.value else []
            mo.vstack(_fb) if _fb else mo.md("")
        """
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
                ok = greek_compare(val, expected, diacritics=strict)
                lbl = lbls[j]
                parts.append(
                    f"{'✓' if ok else '✗'} {lbl} **{val}**" +
                    (f" ← *{expected}*" if not ok else "")
                )
            if parts:
                feedback.append(mo.md(f"*{item[meaning_key]}*: " + " · ".join(parts)))
        return feedback

    # ------------------------------------------- single-input slot drill

    def slot_drill_advance(
        self,
        next_clicked: Any,
        typed_value: str,
        cv: "dict | None",
        remaining: "list | None",
        field_idx: int,
        score: dict,
        fields: "list[tuple[str, str]]",
        all_items: list,
        rand: Any,
        set_cv: Any,
        set_remaining: Any,
        set_field_idx: Any,
        set_score: Any,
    ) -> None:
        """Score the current answer and advance state when the Next button is clicked.

        Call unconditionally inside the next-button handler cell — the function
        is a no-op when *next_clicked* is falsy (button not yet pressed).

        Args:
            next_clicked:  ``next_btn.value`` — truthy after each click.
            typed_value:   ``write_input.value.strip()`` — student's answer.
            cv:            Current item dict from state (``None`` when done).
            remaining:     Remaining items list from state.
            field_idx:     Current field index from state.
            score:         ``{"correct": int, "total": int}`` from state.
            fields:        List of ``(key, label)`` tuples — the question sequence.
            all_items:     Full item list to reshuffle on restart.
            rand:          The ``random`` module from the calling cell.
            set_cv, set_remaining, set_field_idx, set_score:
                           Marimo state setter functions.

        Example handler cell::

            _FIELDS = [('verb', 'словарная форма'), ('sg', 'ед.'), ('pl', 'мн.')]
            gu.slot_drill_advance(
                next_btn.value, write_input.value.strip(),
                cv(), remaining(), field_idx(), score(),
                _FIELDS, VERBS, random,
                set_cv, set_remaining, set_field_idx, set_score,
            )
        """
        if not next_clicked:
            return
        if cv is None:  # done → restart
            shuf = rand.sample(all_items, len(all_items))
            set_cv(shuf[0])
            set_remaining(shuf[1:])
            set_field_idx(0)
            set_score({"correct": 0, "total": 0})
            return
        field_key, _ = fields[field_idx]
        ok = self._ci(typed_value, {cv[field_key]})
        set_score({"correct": score["correct"] + int(ok), "total": score["total"] + 1})
        if field_idx < len(fields) - 1:
            set_field_idx(field_idx + 1)
        elif remaining:
            set_cv(remaining[0])
            set_remaining(remaining[1:])
            set_field_idx(0)
        else:
            set_cv(None)
            set_field_idx(0)

    def slot_drill_display(
        self,
        cv: "dict | None",
        field_idx: int,
        score: dict,
        write_input: Any,
        check_btn: Any,
        next_btn: Any,
        *,
        fields: "list[tuple[str, str]]",
        title: str = "",
        comment: str = "",
        n_items: int = 0,
        meaning_key: str = "meaning",
        prompt_sep: str = "—",
    ) -> Any:
        """Render the current question UI for a single-input slot drill.

        Returns a ``mo.vstack`` element — use as the **last expression** in the
        display cell (no trailing ``return``).

        Args:
            cv:          Current item dict from state (``None`` = done).
            field_idx:   Current field index from state.
            score:       ``{"correct": int, "total": int}`` from state.
            write_input: Diacritics-text widget (from :meth:`diacritics_text`).
            check_btn:   Check button widget.
            next_btn:    Next/advance button widget.
            fields:      List of ``(key, label)`` tuples — must match the handler cell.
            title:       Markdown heading for the exercise (rendered alone above comment).
            comment:     Optional note rendered between title and counter (use ``<br>``
                         for tight line breaks instead of paragraph gaps).
            n_items:     Total number of distinct items (used to compute total questions).
            meaning_key: Key in each item dict used as the prompt.

        Example display cell::

            _FIELDS = [('verb', 'словарная форма'), ('sg', 'ед.'), ('pl', 'мн.')]
            gu.slot_drill_display(
                cv(), field_idx(), score(), write_input, check_btn, next_btn,
                fields=_FIELDS, title="## Упражнение 1", n_items=len(VERBS),
            )
        """
        mo = self._mo
        if cv is None:
            return mo.vstack([
                mo.callout(
                    mo.md(f"Готово! Правильно: **{score['correct']}** / **{score['total']}**"),
                    kind="success",
                ),
                next_btn,
            ])
        field_key, field_label = fields[field_idx]
        typed = write_input.value.strip()
        if check_btn.value and typed:
            ok = self._ci(typed, {cv[field_key]})
            color = "#2d9e2d" if ok else "#d32f2f"
            mark = "✓" if ok else "✗"
            fb = mo.md(
                f'<span style="color:{color};font-weight:bold">'
                f'{mark} {cv[meaning_key]} ({field_label}) → {cv[field_key]}</span>'
            )
        else:
            fb = mo.md(f'*{cv[meaning_key]}* {prompt_sep} **{field_label}**')
        parts: list = []
        if title:
            parts.append(mo.md(title))
        if comment:
            parts.append(mo.md(comment))
        if title:
            parts.append(mo.md(
                f"**{score['total'] + 1}** / {n_items * len(fields)}"
                f" — правильно: {score['correct']}"
            ))
        return mo.vstack(parts + [fb, write_input, mo.hstack([check_btn, next_btn], justify="start")])

    # ------------------------------------------------------- word-form quiz

    def _get_meaning(self, word: dict, lang: str) -> str:
        """Extract the right-language meaning from a word dict."""
        return word.get(
            "meaning" if lang == "ru" else f"meaning_{lang}",
            word.get("meaning", ""),
        )

    def _quiz_done_stop(self, score_dict: dict, lang: str) -> None:
        """Call mo.stop with the standard done-screen (shared by all quiz types)."""
        mo = self._mo
        mo.stop(True, mo.vstack([
            mo.callout(mo.md(_QUIZ_DONE.get(lang, "Done!")), kind="success"),
            mo.md(f"{_QUIZ_CORR.get(lang, 'Correct:')} **{score_dict['correct']}** / **{score_dict['total']}**"),
        ]))

    def word_quiz_question(
        self,
        word: "dict | None",
        all_words: "list[dict]",
        lang: str,
        rng: Any,
    ) -> "tuple":
        """Build a radio-button question for a word-form quiz (Odyssey-style).

        Args:
            word:      Current word dict from state (cv()); None when quiz not started.
            all_words: Full word list used to sample up to 3 distractor forms.
            lang:      UI language (``"ru"``, ``"en"``, or ``"el"``).
            rng:       The ``random`` module from the calling cell.

        Returns ``(answer_radio, word)``.  Calls ``mo.stop`` when *word* is None
        so the cell halts cleanly without raising an exception.

        Expected word dict keys: ``"form"``, ``"lemma"``, ``"context"``,
        optionally ``"meaning"``, ``"meaning_en"``, ``"meaning_el"``.
        """
        mo = self._mo
        if word is None:
            mo.stop(True, mo.md(""))

        _meaning = self._get_meaning(word, lang)
        other_forms = list({q["form"] for q in all_words if q["form"] != word["form"]})
        choices = sorted([word["form"]] + other_forms[:3], key=lambda x: rng.random())
        radio = mo.ui.radio(
            options=choices,
            label=f"«{_meaning}» — _{word['context']}_\n\n{_QUIZ_FORM_LBL.get(lang, 'Form in text:')}",
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
        """
        mo = self._mo

        if w is None:
            if score_dict.get("total", 0) > 0:
                self._quiz_done_stop(score_dict, lang)
            return mo.md("")

        if answer_value is None:
            return mo.md("")

        pos_lbl   = _QUIZ_POS.get(lang, _QUIZ_POS["en"]).get(w.get("pos", ""), w.get("pos", ""))
        gram_lbl  = fmt_ud_feats(w.get("grammar", ""), lang)
        gram_line = " · ".join(filter(None, [pos_lbl, gram_lbl]))

        form, lemma = w["form"], w["lemma"]
        word_info = f"**{form}**" if form == lemma else f"**{form}** → **{lemma}**"
        correct = answer_value == form

        if correct:
            tbl = mo.md("")
            if build_paradigm_table is not None:
                try:
                    tbl_html = build_paradigm_table(w, lang=lang)
                    tbl = mo.Html(tbl_html) if tbl_html else mo.md("")
                except Exception as e:
                    tbl = mo.md(f"_{e}_")
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

    # ------------------------------------------------------- write-word quiz

    def ensure_file(self, filename: str, *, nb_dir: Any, remote_base: str, timeout: int = 30) -> Any:
        """Return path to *filename* inside *nb_dir*, downloading from *remote_base* if absent."""
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
                raise RuntimeError(
                    f"ensure_file: could not fetch {filename!r}\n"
                    f"  local path checked: {local.resolve()}\n"
                    f"  remote URL tried:   {url}\n"
                    f"  error: {exc}"
                ) from exc
            finally:
                socket.setdefaulttimeout(prev)
        return local

    def load_vocab_tsv(self, *filenames: str, nb_dir: Any, remote_base: "str | None" = None) -> "list[dict]":
        """Load one or more Word/Translation TSVs and return vocab word dicts.

        Each dict contains ``form``, ``meaning``, ``lemma``, ``context``.
        Missing files are downloaded from *remote_base* when provided.
        """
        import pandas as _pd
        from pathlib import Path

        dfs = []
        for filename in filenames:
            local = Path(nb_dir) / filename
            if not local.exists():
                if remote_base is None:
                    raise FileNotFoundError(f"{filename} not found locally and no remote_base provided")
                self.ensure_file(filename, nb_dir=nb_dir, remote_base=remote_base)
            dfs.append(_pd.read_csv(local, sep="\t"))

        _df = _pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
        result = []
        for _, r in _df.iterrows():
            word = str(r.get("Word", "")).strip()
            if not word:
                continue
            meaning = str(r.get("Translation", "")).strip()
            result.append({"form": word, "meaning": meaning, "lemma": word, "context": meaning})
        return result

    def word_write_question(self, word: "dict | None", lang: str) -> "tuple":
        """Return *(mo.ui.text, word)* for a write-the-word exercise.

        Calls ``mo.stop`` when *word* is ``None`` so the cell halts cleanly.
        Use a ``None`` guard in the calling cell (like ``word_quiz_question``).
        """
        mo = self._mo
        if word is None:
            mo.stop(True, mo.md(""))
        return mo.ui.text(
            placeholder=_WRITE_PLACEHOLDER.get(lang, "Greek word…"),
            full_width=True,
        ), word

    def word_write_feedback(
        self,
        input_widget: Any,
        word: "dict | None",
        score_dict: dict,
        lang: str,
    ) -> Any:
        """Question/feedback slot for write-the-word exercise.

        Returns italic meaning when input is empty, colored ✓/✗ when typed.
        When *word* is ``None`` and ``total > 0``, calls ``mo.stop`` with a done screen.
        """
        mo = self._mo
        if word is None:
            if score_dict.get("total", 0) > 0:
                self._quiz_done_stop(score_dict, lang)
            return mo.md("")

        _meaning = self._get_meaning(word, lang)
        val = input_widget.value
        if not val:
            return mo.md(f"*{_meaning}*")

        _ok = self._ci(val.strip(), {word["form"]})
        _color = "#2d9e2d" if _ok else "#d32f2f"
        _mark = "✓" if _ok else "✗"
        return mo.md(f'<span style="color:{_color};font-weight:bold">{_mark} {_meaning} → {word["form"]}</span>')

    def diacritics_text(self, *, placeholder: str = "", label: str = "") -> Any:
        """Combined diacritics bar + text input; wraps :func:`diacritics_text`."""
        return diacritics_text(self._mo, placeholder=placeholder, label=label)
