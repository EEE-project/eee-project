"""Top-level helper functions relocated here from notebook_utils.py (verbatim,
zero behavior change) to keep that module to a more manageable size. Not a
public entry point -- notebook_utils.py re-exports every name from here, so
existing ``from eee_project import X`` / ``from eee_project.notebook_utils
import X`` call sites keep resolving unchanged.
"""

from __future__ import annotations

import csv
import functools
import importlib.resources
import re as _re
import unicodedata as _unicodedata
from typing import Any

from eee_project._grammar_fmt import fmt_ud_feats, _FMT_CASE, _FMT_NUM, _FMT_VFORM, _FMT_MOOD
from eee_project._registry import register_backend, set_chain


def load_ga_config(path=None) -> "dict | None":
    """Load GA config from a ``ga.json`` file that lives outside the repository.

    Args:
        path: Pass ``__file__`` from a notebook cell to look for ``ga.json``
              next to the notebook. Pass a directory path or an explicit
              ``ga.json`` path for other local layouts. Pass an
              ``http(s)://`` URL to fetch ``ga.json`` remotely instead — the
              pattern a real deployed WASM notebook needs, since it has no
              local filesystem to read from at runtime (see below). Pass
              ``None`` (default) to search the current working directory.

    Returns a dict such as ``{"measurement_id": "G-XXXXXXXXXX"}``, or
    ``None`` if the file is not found/fetchable — GA is silently disabled.

    Example cell (local dev)::

        _ga = load_ga_config(__file__)
        eee_topbar(mo, back_url="...", lang=lang, titles=TITLES, ga_config=_ga)

    Example cell (deployed WASM export, no navigation/index.tsv needed —
    for that case use :class:`ConfigStore`'s ``from_url``/``from_file_or_url``
    instead, which fetch ``ga.json`` the same way alongside real lessons)::

        _ga = load_ga_config(f"{_ROOT}/ga.json")  # _ROOT: repo's raw-content URL

    For **local-only** use (this function read directly off disk, no
    WASM/molab deployment), keep ``ga.json`` out of the repository — add it
    to ``.gitignore``. For the URL form, ``ga.json`` must be committed for
    the fetch to succeed. A GA measurement ID isn't a secret (every page
    load exposes it in plain network requests anyway), so committing it for
    that case is correct, not an oversight. Minimal content::

        {"measurement_id": "G-XXXXXXXXXX"}
    """
    import json as _json
    from pathlib import Path as _Path

    if isinstance(path, str) and path.startswith(("http://", "https://")):
        return _fetch_json_url(path)

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


def _parse_codeberg_raw_url(url: str) -> "tuple[str, str, str, str] | None":
    """Parse a Codeberg raw-content URL into (owner, repo, branch, path).

    Returns None if the URL is not Codeberg-shaped.
    """
    m = _re.match(r"^https://codeberg\.org/([^/]+)/([^/]+)/raw/branch/([^/]+)/(.+)$", url)
    return m.groups() if m else None


def _cors_safe_raw_url(url: str) -> str:
    """Rewrite a git-forge raw-content URL to a form that sends CORS headers.

    Codeberg's and GitLab's plain git-web raw endpoints
    (``.../raw/branch/<branch>/...``, ``.../-/raw/<branch>/...``) send no
    ``Access-Control-Allow-Origin`` header — confirmed via direct response
    header dump, not assumed — so a browser ``fetch``/``urllib`` call from
    inside a self-hosted marimo WASM/Pyodide export is silently blocked by
    CORS, even though the identical URL works fine from ``curl`` (which
    doesn't enforce CORS at all). Their REST APIs serve the identical
    bytes with ``access-control-allow-origin: *``. GitHub's own raw
    endpoint (``raw.githubusercontent.com``) already sends CORS headers,
    so it — and any other URL this doesn't recognize — passes through
    unchanged. Only called at an actual network-fetch site (never for a
    human-facing click-through link like :func:`magnify_image`'s
    ``raw_base``, which deliberately keeps the git-web form).

    First rewrites the URL to match the actual serving host (if not Codeberg),
    then applies CORS-safe transformations on top.
    """
    import urllib.parse

    # Rehost to the actual serving host first, if not already there
    url = _rehost_raw_url(url)

    # Codeberg raw → CORS-safe API form
    parts = _parse_codeberg_raw_url(url)
    if parts:
        owner, repo, branch, path = parts
        return f"https://codeberg.org/api/v1/repos/{owner}/{repo}/raw/{path}?ref={branch}"

    # GitLab raw → CORS-safe API form
    m = _re.match(r"^https://gitlab\.com/([^/]+)/([^/]+)/-/raw/([^/]+)/(.+)$", url)
    if m:
        owner, repo, branch, path = m.groups()
        project = urllib.parse.quote(f"{owner}/{repo}", safe="")
        # path's segments may already be percent-encoded (e.g. ensure_file()
        # pre-quotes a non-ASCII filename before building the raw URL this
        # function receives) -- only the '/' separators need to become %2F
        # for GitLab's file_path parameter; re-quoting the whole path would
        # double-encode any '%' already present.
        file_path = path.replace("/", "%2F")
        return f"https://gitlab.com/api/v4/projects/{project}/repository/files/{file_path}/raw?ref={branch}"

    return url


def _rehost_raw_url(url: str) -> str:
    """Rewrite a Codeberg-shaped raw-content URL to whichever host is
    actually serving this page, if not Codeberg. Unrecognized URLs (already
    GitHub/GitLab-shaped, or anything else) pass through unchanged.

    ``owner``/``repo`` are wildcarded, not hardcoded to any one repo -- this
    is what makes the rewrite apply identically to created_with_eee's own
    fetches and to any second repo (e.g. greek-knowledge-eee) a notebook
    fetches from, with no per-repo code path to add later.
    """
    parts = _parse_codeberg_raw_url(url)
    if not parts:
        return url
    owner, repo, branch, path = parts
    host_base = _source_host_base()
    if host_base.startswith("https://github.com"):
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    if host_base.startswith("https://gitlab.com"):
        return f"https://gitlab.com/{owner}/{repo}/-/raw/{branch}/{path}"
    return url  # already Codeberg -- _cors_safe_raw_url handles CORS-safety next


def _fetch_url_bytes(url: str, timeout: "int | float") -> bytes:
    """GET *url* synchronously and return the raw response body.

    Under Pyodide, ``urllib.request.urlopen`` goes through ``pyodide_http``'s
    patched implementation, which raises ``UnicodeEncodeError`` ("'ascii'
    codec can't encode...") whenever a response header contains non-ASCII
    bytes — confirmed via a diagnostic traceback pointing inside
    ``pyodide_http/_urllib.py`` itself, not anything on the caller's side.
    Codeberg's raw-content API triggers this for any non-ASCII filename: it
    sends the primary ``Content-Disposition: ...; filename="<raw UTF-8>"``
    parameter un-percent-encoded (RFC 7230/6266 permit this; only the
    fallback ``filename*=UTF-8''...`` parameter is required to be encoded).

    So under Pyodide (``sys.platform == "emscripten"``) this bypasses
    ``pyodide_http`` entirely with a raw synchronous ``XMLHttpRequest`` —
    marimo's Pyodide kernel runs in a Web Worker, where synchronous XHR is
    allowed (unlike the main thread, where it's deprecated) — since only
    the status and binary body are needed here, the problematic header is
    never touched at all. Plain CPython (local dev, no non-ASCII-header
    bug to work around) uses ``urllib.request.urlopen`` as normal.
    """
    import sys

    if sys.platform == "emscripten":
        from js import XMLHttpRequest, Uint8Array

        xhr = XMLHttpRequest.new()
        xhr.open("GET", url, False)
        xhr.responseType = "arraybuffer"
        # timeout is legal on a synchronous XHR specifically when the global
        # is a Worker, not a Window -- true here, since that's exactly where
        # marimo runs the Pyodide kernel (see this function's docstring).
        xhr.timeout = timeout * 1000
        xhr.send(None)
        if not (200 <= xhr.status < 300):
            import urllib.error
            raise urllib.error.HTTPError(url, xhr.status, xhr.statusText, {}, None)
        return Uint8Array.new(xhr.response).to_py().tobytes()

    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as _resp:
        return _resp.read()


def _fetch_json_url(url: str, timeout: "int | float" = 5) -> "dict | None":
    """Fetch *url* (CORS-rewritten) and parse it as JSON; ``None`` on any
    fetch/parse failure. Used by :func:`load_ga_config`'s URL branch.

    :meth:`ConfigStore.from_url` fetches its own ``ga=<url>`` the same way
    but keeps its own inline copy rather than calling this: there, a ga-fetch
    failure is meant to also blank out already-fetched lessons (one shared
    try/except covers both), which swallowing the error in here would break.
    """
    import json as _json

    try:
        return _json.loads(_fetch_url_bytes(_cors_safe_raw_url(url), timeout).decode("utf-8"))
    except Exception:
        return None


async def _fetch_url_bytes_async(url: str, timeout: "int | float") -> bytes:
    """Async GET *url*, returning the raw response body.

    Exists so multiple fetches can run concurrently via ``asyncio.gather``
    (see :meth:`GreekUtils.ensure_files`) — genuine network-level overlap,
    not just interleaved scheduling. Real OS threads aren't an option here:
    Pyodide's thread support needs COOP/COEP response headers, which
    Codeberg Pages (this project's deployment target) doesn't send, so
    ``concurrent.futures.ThreadPoolExecutor`` would silently run single
    -threaded anyway. Async is the only mechanism that actually overlaps
    requests in that environment.

    Under Pyodide this uses ``pyodide.http.pyfetch()``, whose response
    reads the non-ASCII ``Content-Disposition`` header just like
    ``fetch()`` does natively (no ``pyodide_http`` monkeypatch involved),
    so the bug ``_fetch_url_bytes`` works around never applies here. Plain
    CPython runs the existing synchronous fetch in a thread so it doesn't
    block the event loop. ``pyfetch()`` has no built-in timeout (unlike
    XHR's native ``.timeout``), so it's enforced with ``asyncio.wait_for``
    instead.
    """
    import asyncio
    import sys

    if sys.platform == "emscripten":
        from pyodide.http import pyfetch

        async def _do() -> bytes:
            response = await pyfetch(url, method="GET")
            if not response.ok:
                import urllib.error
                raise urllib.error.HTTPError(url, response.status, response.status_text, {}, None)
            return await response.bytes()

        return await asyncio.wait_for(_do(), timeout=timeout)

    return await asyncio.to_thread(_fetch_url_bytes, url, timeout)


@functools.lru_cache(maxsize=32)
def parent_back_url(parent_url: str, *, timeout: int = 5) -> "str | None":
    """Resolve ``eee_topbar``'s ``back_url`` for a course/grouping-index page.

    Fetches the *parent* index's own ``index.tsv`` over the network and
    returns its ``index_url``. Every row in a grouping-level ``index.tsv``
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
        parent_url: Remote URL of the parent's ``index.tsv``.
        timeout:    Network timeout in seconds.

    Example cell (course index one level below a grouping index)::

        from eee_project.notebook_utils import parent_back_url
        back_url = parent_back_url(
            f"{_ROOT}/modern_greek/b1greeklanguageandculture/index.tsv",
        )
        eee_topbar(mo, back_url=back_url, lang=lang, titles=TITLES, style="index")
    """
    from eee_project.notebook_utils import ConfigStore
    return ConfigStore.from_url(parent_url, timeout=timeout).index_url()


@functools.lru_cache(maxsize=1)
def _source_host_base() -> str:
    """Return the EEE org URL for whichever host is actually serving this page.

    Detected via Pyodide's ``js`` bridge to ``self.location.hostname`` —
    only available when running as a WASM export in a real browser. Uses
    ``self``, not ``window``: marimo's Pyodide kernel runs in a Web Worker,
    which has no ``window`` global (confirmed directly — ``from js import
    window`` raises ``ImportError`` there); ``self`` is the Worker's own
    global scope and still exposes ``location``. Falls back to Codeberg
    (the canonical dev host) for local ``marimo edit``/``marimo run`` and
    any other environment without that bridge.

    Cached with maxsize=1 since the hostname is invariant for the life of
    the running page/kernel.
    """
    try:
        from js import self as _self
        hostname = _self.location.hostname
    except Exception:
        return "https://codeberg.org/EEE-project"
    if hostname.endswith("github.io"):
        return "https://github.com/EEE-project"
    if hostname.endswith("gitlab.io"):
        return "https://gitlab.com/EEE-project"
    return "https://codeberg.org/EEE-project"


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
    import anywidget as _anywidget
    return type("_GaTag", (_anywidget.AnyWidget,), {
        "_esm": _make_ga_esm(measurement_id),
    })


def save_language_selection(bridge, selector) -> None:
    """Persist *selector*'s current value via *bridge* (see
    :func:`language_bridge`). No-op if *bridge* is ``None``.

    Call from a cell depending on both *bridge* and *selector*. Skips
    writing until *bridge* has reported back a real (possibly empty)
    stored value — otherwise, on every fresh page load, this would
    write *selector*'s placeholder default over a real stored value
    before the (async) browser read has had a chance to apply it: the
    write is synchronous, the read isn't, so an unconditional write
    would win that race every time.
    """
    if bridge is None:
        return
    stored = getattr(bridge, "stored", None)
    if stored is not None:
        bridge.save = selector.value


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


_STANZA_RANGE_RE = _re.compile(r"^([IVXLCDM]+)\.(\d+)[–-](\d+)")


def _parse_stanza_range(ref: str) -> "tuple[str, int, int] | None":
    m = _STANZA_RANGE_RE.match(ref)
    if not m:
        return None
    book, start, end = m.groups()
    return book, int(start), int(end)


def find_stanza_translation(ref: str, translations: dict, *, allow_coarse_fallback: bool = True) -> str:
    """Look up ``ref`` (a :func:`parse_stanza_text` key, e.g. ``"IX.39-42"``)
    in a translator's ``{stanza_ref: text}`` dict (one value of
    :func:`parse_stanza_translations`'s first return value), falling back to
    a coarser stored range that fully contains it when there's no exact key
    match -- e.g. a translator whose own line breaks don't match the source
    text's stanza boundaries may be transcribed against wider spans instead
    (``"IX.39-46 (equivalent passage)"`` covering what the source splits into
    ``"IX.39-42"`` and ``"IX.43-46"``). Both ``ref`` and the stored keys must
    start with ``<book>.<start>-<end>`` (ASCII hyphen or en dash); a ref that
    doesn't parse this way, or has no matching or containing entry, returns
    ``"—"``.

    Pass ``allow_coarse_fallback=False`` to require an exact key match and
    return ``"—"`` otherwise. Use this for a translator whose stored ranges
    are expected to already align with the course's own stanza split (e.g.
    a word-for-word interlinear crib) -- a coarser match there means extra,
    unrelated lines bleeding in from a neighboring stanza rather than a
    genuine equivalent-passage transcription, so showing nothing is more
    honest than showing the wrong text.
    """
    if ref in translations:
        return translations[ref]
    if not allow_coarse_fallback:
        return "—"
    parsed = _parse_stanza_range(ref)
    if parsed is None:
        return "—"
    book, start, end = parsed
    for stored_ref, text in translations.items():
        stored = _parse_stanza_range(stored_ref)
        if stored and stored[0] == book and stored[1] <= start and end <= stored[2]:
            return text
    return "—"


def interlinear_translator_key(lang: str) -> str:
    """The translator-dict key for *lang*'s word-for-word interlinear crib
    -- ``"interlinear_ru"``, ``"interlinear_en"``, ``"interlinear_el"``, etc.

    Matches ``greek-knowledge-eee``'s own ``## interlinear_{lang}`` section
    naming convention (one value of :func:`parse_stanza_translations`'s
    first return value). A caller building a language-aware translator
    picker should use this instead of hardcoding the string, so a language
    mismatch here (a notebook assuming a different name than the KB
    actually uses) can't silently make the interlinear option show no
    text -- this happened once with Russian, whose old pre-KB local file
    called it ``"подстрочник"`` instead.
    """
    return f"interlinear_{lang}"


def strip_comment_lines(text: str) -> str:
    """Drop any ``<!-- ... -->`` line from stanza text, keeping the rest.

    Works on any translator's already-extracted text (from
    :func:`parse_stanza_translations`, which doesn't strip mid-stanza
    comments itself) -- a safe no-op for a translator with no such lines.
    Lets a stanza body carry out-of-band annotations alongside its real
    text (e.g. an interlinear translator's echoed Greek source line,
    ``<!-- grc: ... -->``, or any future note tag) without callers needing
    to know which tag is in use.
    """
    return "\n".join(
        L for L in text.splitlines()
        if not ((s := L.strip()).startswith("<!--") and s.endswith("-->"))
    )


def greek_compare(
    a: str,
    b: str,
    *,
    case_sensitive: bool = False,
    diacritics: bool = False,
) -> bool:
    """Compare two Greek strings with configurable normalization.

    Works for both Modern and Ancient Greek, and for both single grammatical
    forms and full phrases: punctuation is always treated as a word
    separator, not compared -- a trailing "?"/";"/"..." or a stray comma
    never affects the result, and runs of whitespace collapse to one
    separator. A no-op for a plain single-word form (nothing to strip),
    so this doesn't change behavior for the vast majority of existing
    callers (paradigm-drill checkers comparing one declined/conjugated
    form) -- only phrase-comparison callers (multi-word text) are affected.

    Args:
        case_sensitive: If ``False`` (default), comparison ignores case.
        diacritics:     If ``False`` (default), diacritical marks are stripped
                        before comparison. If ``True``, NFC-normalized forms
                        must match exactly (including accents).

    Example::

        greek_compare("λεγε", "λέγε")                        # True
        greek_compare("λεγε", "λέγε", diacritics=True)       # False
        greek_compare("Λέγε", "λέγε", case_sensitive=True)   # False
        greek_compare("Έχεις κανένα σχέδιο", "Έχεις κανένα σχέδιο;")  # True
    """
    def _norm(s: str) -> str:
        if not diacritics:
            s = strip_diacritics(s)
        else:
            s = _unicodedata.normalize("NFC", s)
        if not case_sensitive:
            s = s.lower()
        # Punctuation is a separator between words, not content to compare --
        # replace any run of non-word characters with a single space, then
        # split/rejoin to also collapse whitespace runs (handles a phrase's
        # trailing "?"/";"/"..." and multiple spaces alike). \w matches Greek
        # letters correctly under Python 3's default Unicode regex.
        return " ".join(_re.sub(r"[^\w\s]+", " ", s).split())
    return _norm(a) == _norm(b)


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

    Discovers language files by name (``ui-*.tsv``) rather than a fixed
    ``("en", "ru", "el")`` tuple, so adding a new language is purely a data
    change -- drop in ``ui-{lang}.tsv`` with the same ``Key``/``label``
    columns and it's picked up with no code change.
    """
    pkg = importlib.resources.files("eee_project.data.labels")
    labels: dict = {}
    for entry in pkg.iterdir():
        m = _re.fullmatch(r"ui-([a-z]{2})\.tsv", entry.name)
        if not m:
            continue
        lang = m.group(1)
        text = entry.read_text(encoding="utf-8")
        for row in csv.DictReader(text.splitlines(), delimiter="\t"):
            labels.setdefault(row["Key"], {})[lang] = row["label"]
    return labels


_UI_LABELS = _load_ui_labels()
# Every language _load_ui_labels() discovered -- reused by module-level dicts
# below (_GRC_TCOL etc.) that need "all known languages" without hardcoding
# ("ru", "en", "el") themselves, so those dicts also pick up a new language
# with no code change, same as a plain _ui_label() call does.
_UI_LANGS = sorted({lang for entry in _UI_LABELS.values() for lang in entry})


def _ui_label(key: str, lang: "str | None" = None) -> str:
    """Module-level twin of :meth:`GreekUtils.ui_label`, so module-level
    functions (e.g. ``eee_footer``, which has no ``self``) can share the
    same lookup instead of a separate copy."""
    lang = lang or "en"
    entry = _UI_LABELS.get(key, {})
    return entry.get(lang) or entry.get("en") or key


def _lang_map(keys, tsv_key) -> dict:
    """Build a ``{lang: {key: label}}`` dict for a *compound* concept (a
    tense code, a verb-tense column, a voice) that has no single matching
    ``_grammar_fmt.py`` dict to derive from -- each ``key`` becomes its own
    flat ``ui-{lang}.tsv`` row via ``tsv_key(key)``, so (like every other
    ``_ui_label()`` lookup) a new language is still a data-only change."""
    return {lang: {k: _ui_label(tsv_key(k), lang) for k in keys} for lang in _UI_LANGS}


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


# ══════════════════════════════ grc paradigm display ══

# _GRC_NL/_GRC_DL/_GRC_PROW/_GRC_INF_LBL/_GRC_IMP_LBL are all DERIVED from
# _grammar_fmt.py's _FMT_NUM/_FMT_VFORM/_FMT_MOOD (verified byte-identical
# to the hand-authored values they replace) rather than re-authored, for
# the same reason as the _QUIZ_* dicts above -- _GRC_PROW specifically
# reuses fmt_ud_feats() itself (also verified byte-identical), since
# "{person} {number}" is exactly what that formatter already builds.
# _GRC_TCOL's codes (PAI/IAI/AAI/AMI/API/XAI/YAI) are Tense+Aspect+Voice
# compounds with no matching _FMT_* dict to derive from (there's no
# _FMT_ASPECT, and _FMT_TENSE alone can't distinguish imperfect from
# aorist -- both "Past"), so its 7 codes are individual ui-{lang}.tsv keys
# (grc_tense_pai etc.) via the shared _lang_map() helper instead -- same
# as the default caption below -- rather than a hand-authored per-language
# literal, so a new language is still a data-only change.

_GRC_NL = {lang: (d['Sing'].capitalize(), d['Plur'].capitalize()) for lang, d in _FMT_NUM.items()}
# dual column label -- pronoun-only; nouns/adjectives have no dual axis
_GRC_DL = {lang: d['Dual'].capitalize() for lang, d in _FMT_NUM.items()}
_GRC_TCOL = _lang_map(("PAI", "IAI", "AAI", "AMI", "API", "XAI", "YAI"),
                       lambda code: f"grc_tense_{code.lower()}")
_GRC_PROW = {
    lang: {f"{p}{suf}": fmt_ud_feats(f"Person={p}|Number={full}", lang)
           for p in "123" for suf, full in (("S", "Sing"), ("D", "Dual"), ("P", "Plur"))}
    for lang in _UI_LANGS
}
_GRC_INF_LBL = {lang: d['Inf'].capitalize() for lang, d in _FMT_VFORM.items()}
_GRC_IMP_LBL = {
    lang: {f"2{suf}": f"{_FMT_MOOD[lang]['Imp'].capitalize()} 2{d[full].rstrip('.')}."
           for suf, full in (("S", "Sing"), ("D", "Dual"), ("P", "Plur"))}
    for lang, d in _FMT_NUM.items()
}
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

    _default_lang = lang  # captured before build_paradigm_table's own `lang` param shadows this name

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
        the two are the same word) — see load_vocab_tsv's docstring. ``lang``
        (``ru``/``en``/``el``) picks the table's own row/column labels;
        defaults to the builder's own ``lang`` when omitted.
        """
        _lang = lang or _default_lang
        lemma, pos, tested = _lemma_of(w, w["form"]), w["pos"], w["form"]
        _lex = _backend or ag_backend
        tn = _norm_grc(tested)
        found = False
        any_forms = False
        sg_lbl, pl_lbl = _GRC_NL[_lang]
        _case_lbl = _FMT_CASE.get(_lang, _FMT_CASE["en"])
        _prow = _GRC_PROW.get(_lang, _GRC_PROW["en"])
        # Fallback table caption when neither _cap nor w["lexicon_tag"] is given.
        _default_cap = _ui_label("grc_default_caption", _lang)

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
                tbl += f'<tr><td style="{_GRC_ROW}">{_case_lbl.get(_GRC_CASE_KEY[c], c)}</td>'
                for n in numbers:
                    tbl += _td(ag_rows[(c, n)])
                tbl += "</tr>"
            return tbl + "</table>"

        if pos == "noun":
            ag_rows = _collect_rows(_ag_slots("noun"), ["N", "G", "D", "A", "V"], "noun")
            _ag_has = any(ag_rows.values())
            be_lbl = (_cap or w.get("lexicon_tag") or _default_cap) if _ag_has else "unimorph"
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

            _tcol = _GRC_TCOL.get(_lang, _GRC_TCOL["en"])
            _imp_lbl = _GRC_IMP_LBL.get(_lang, _GRC_IMP_LBL["en"])
            tenses = [(t, _tcol.get(t, t)) for t in ["PAI", "IAI", "AAI", "AMI", "API", "XAI", "YAI"]
                      if any(_vf(f"{t}.{ps}") for ps in _PS)]
            if not tenses:
                return None
            tbl = (
                f'<table style="border-collapse:collapse;font-size:.95em;margin-top:8px">'
                f'<caption style="{_GRC_CAP}">{_cap or w.get("lexicon_tag") or _default_cap}</caption>'
                f'<tr><th style="{_GRC_TH}"></th>'
            )
            tbl += "".join(f'<th style="{_GRC_TH}">{lbl}</th>' for _, lbl in tenses) + "</tr>"
            for ps in _PS:
                tbl += f'<tr><td style="{_GRC_ROW}">{_prow.get(ps, ps)}</td>'
                for t, _ in tenses:
                    tbl += _td(_vf(f"{t}.{ps}"))
                tbl += "</tr>"
            _INF_MAP = {"PAI": "PAN", "IAI": "IAN", "AAI": "AAN", "AMI": "AMN", "API": "APN"}
            if any(_vf(_INF_MAP.get(t, "")) for t, _ in tenses):
                tbl += f'<tr><td style="{_GRC_ROW}">{_GRC_INF_LBL.get(_lang, _GRC_INF_LBL["en"])}</td>'
                for t, _ in tenses:
                    tbl += _td(_vf(_INF_MAP.get(t, "")))
                tbl += "</tr>"
            _IMP_MAP = {"PAI": "PAD", "AAI": "AAD", "AMI": "AMD"}
            for imp_ps, imp_sfx in [("2S", ".2S"), ("2D", ".2D"), ("2P", ".2P")]:
                if any(_vf(f"{_IMP_MAP[t]}{imp_sfx}") for t, _ in tenses if t in _IMP_MAP):
                    tbl += f'<tr><td style="{_GRC_ROW}">{_imp_lbl.get(imp_ps, imp_ps)}</td>'
                    for t, _ in tenses:
                        imp_t = _IMP_MAP.get(t)
                        tbl += _td(_vf(f"{imp_t}{imp_sfx}")) if imp_t else f'<td style="{_GRC_TD}">—</td>'
                    tbl += "</tr>"
            tbl += "</table>"

        elif pos == "adj":
            ag_rows = _collect_rows(_ag_slots("adjective"), ["N", "G", "D", "A"], "adjective")
            if not any(ag_rows.values()):
                return None
            tbl = _case_table(_cap or w.get("lexicon_tag") or _default_cap, ["N", "G", "D", "A"], ag_rows)

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
                tbl = _case_table(_cap or w.get("lexicon_tag") or _default_cap, ["N", "G", "D", "A"], pron_rows,
                                   numbers=_PN_COLS, num_labels=[_prow[pn] for pn in _PN_COLS])
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
                tbl = _case_table(_cap or w.get("lexicon_tag") or _default_cap, ["N", "G", "D", "A"], ag_rows,
                                   numbers=("S", "P", "D"), num_labels=(sg_lbl, pl_lbl, _GRC_DL.get(_lang, _GRC_DL["en"])))

        else:
            return None

        if not any_forms:
            return None
        if not found:
            if hide_if_absent:
                return None
            _missing = _ui_label('word_missing_in_paradigm', _lang).format(word=f"<b>{tested}</b>", lemma=lemma)
            note = f'<div style="{_GRC_NOTE}">{_missing}</div>'
            return note + tbl
        return tbl

    return build_paradigm_table


# ── Modern-Greek (el) diachronic paradigm renderer (parallel to the grc one) ──
_EL_CASES = ["Nom", "Gen", "Acc", "Voc"]        # Modern nouns/adj: 4 cases, no dative
_EL_VERB_COLS = [                               # (slug, base features, particle)
    ("pres",     {"Tense": "Pres", "Mood": "Ind"},                  ""),
    ("impf",     {"Tense": "Past", "Aspect": "Imp",  "Mood": "Ind"}, ""),
    ("aor",      {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind"}, ""),
    ("fut",      {"Tense": "Fut",  "Aspect": "Perf", "Mood": "Ind"}, "θα"),
    ("fut_cont", {"Tense": "Fut",  "Aspect": "Imp",  "Mood": "Ind"}, "θα"),
    ("subj",     {"Mood": "Sub",   "Aspect": "Perf"},                "να"),
    ("imp",      {"Mood": "Imp",   "Aspect": "Perf"},                ""),
]
# Like _GRC_TCOL above: _EL_VERB_COL_LBL/_EL_VOICE_CAP are compound-keyed
# (tense-slug / Act-Pass) with no matching _FMT_* dict, so their entries are
# individual ui-{lang}.tsv keys (via the shared _lang_map() helper) rather
# than a hand-authored per-language literal -- a new language is still a
# data-only change.
_EL_VERB_COL_LBL = _lang_map([slug for slug, _, _ in _EL_VERB_COLS], lambda slug: f"el_verb_col_{slug}")
_EL_VOICE_CAP = _lang_map(("Act", "Pass"), lambda v: f"el_voice_cap_{v.lower()}")


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
    from modern_greek_inflexion_eee import PRONOUN_LEMMAS_INDECLINABLE

    _default_lang = lang  # captured before build_paradigm_table's own `lang` param shadows this name

    @functools.lru_cache(maxsize=None)
    def _el_slots(pos):
        t = el_backend.get_slot_templates("el", pos, lang)
        return {} if t is None else {frozenset(s.features.items()): s for s in t}

    def build_paradigm_table(
        w: dict, *, lang: "str | None" = None, _backend: Any = None,
        _cap: "str | None" = None, hide_if_absent: bool = False,
    ) -> "str | None":
        _lang = lang or _default_lang
        lemma = poly_to_mono(_lemma_of(w, w["form"]))
        pos = w["pos"]
        tested = strip_diacritics(w["form"]).lower()
        be = _backend or el_backend
        any_forms = False
        sg_lbl, pl_lbl = _GRC_NL[_lang]
        _case_lbl = _FMT_CASE.get(_lang, _FMT_CASE["en"])
        _prow = _GRC_PROW.get(_lang, _GRC_PROW["en"])

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

        def _case_num_table(pos_str):
            """Case x Number table, genders unioned per cell -- shared shape
            for noun/adjective/pronoun(gendered): all three resolve through
            _gendered_case_num_rows() on the backend side (Case x Number x
            Gender), so the same 3-gender union loop applies unchanged.
            """
            rows = {}
            for c in _EL_CASES:
                for nl, n in (("S", "Sing"), ("P", "Plur")):
                    fs = set()
                    for g in ("Masc", "Fem", "Neut"):
                        fs |= _forms({"Case": c, "Number": n, "Gender": g}, pos_str)
                    rows[(c, nl)] = fs
            if not any(rows.values()):
                return None
            tbl = (
                f'<table style="border-collapse:collapse;font-size:.95em;margin-top:8px">'
                f'<caption style="{_GRC_CAP}">{_html.escape(_cap or _ui_label("el_default_caption", _lang))}</caption>'
                f'<tr><th style="{_GRC_TH}"></th>'
                f'<th style="{_GRC_TH}">{sg_lbl}</th><th style="{_GRC_TH}">{pl_lbl}</th></tr>'
            )
            for c in _EL_CASES:
                tbl += f'<tr><td style="{_GRC_ROW}">{_case_lbl.get(c, c)}</td>'
                tbl += _td(rows[(c, "S")]) + _td(rows[(c, "P")]) + "</tr>"
            return tbl + "</table>"

        if pos in ("noun", "adjective"):
            result = _case_num_table(pos)
            if result is None:
                return None

        elif pos == "pronoun":
            # Only the "gendered" pronoun family (κανένας, ίδιος, αυτός, ...
            # -- Case x Number x Gender, same shape as noun/adjective) has a
            # sensible table here. Personal (εγώ/εσύ) also resolves
            # correctly through the same path -- mg_pron_path("personal",
            # ...) ignores the Gender key entirely and reads Case+Number,
            # verified empirically (backend.inflect('εγώ', {Case, Number,
            # Gender}, 'pronoun') returns the real per-case/number forms).
            # Indeclinable (πού/πότε) does NOT: mg_pron_path("indeclinable",
            # ...) ignores Case/Number/Gender entirely and always returns
            # the same single cell, so every table cell would render the
            # identical invariant word -- confirmed empirically
            # (backend.inflect('πού', ...) returns {'πού'} for all 8
            # case/number combinations) -- which misrepresents a word that
            # doesn't decline at all as if it does. Skip those; matches
            # this function's existing "no table" behavior for unsupported
            # pos values elsewhere.
            if lemma in PRONOUN_LEMMAS_INDECLINABLE:
                return None
            result = _case_num_table(pos)
            if result is None:
                return None

        elif pos == "verb":
            _PS = [("1", "Sing", "1S"), ("2", "Sing", "2S"), ("3", "Sing", "3S"),
                   ("1", "Plur", "1P"), ("2", "Plur", "2P"), ("3", "Plur", "3P")]
            _voice_cap = _EL_VOICE_CAP.get(_lang, _EL_VOICE_CAP["en"])
            _col_lbl = _EL_VERB_COL_LBL.get(_lang, _EL_VERB_COL_LBL["en"])
            tables = []
            for voice, vcap in (("Act", _voice_cap["Act"]), ("Pass", _voice_cap["Pass"])):
                grid, cols = {}, []
                for slug, base, part in _EL_VERB_COLS:
                    clbl = _col_lbl[slug]
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
                    tbl += f'<tr><td style="{_GRC_ROW}">{_prow.get(ps, ps)}</td>'
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


def _strip_grc_caption(h: str) -> str:
    return _re.sub(r'<caption[^>]*>.*?</caption>', '', h)


_GRC_PERIOD_HDR_STYLE = "font-size:.82em;color:#374151;font-weight:600;margin-top:10px;margin-bottom:1px"
_GRC_PERIOD_DESC_STYLE = "font-size:.72em;color:#9ca3af;margin-bottom:5px"


def _wrap_grc_period_html(label: str, descr_key: str, raw: str) -> str:
    hdr = f'<div style="{_GRC_PERIOD_HDR_STYLE}">{label}</div>'
    dsc = f'<div style="{_GRC_PERIOD_DESC_STYLE}">{_GRC_LEX_DESCR.get(descr_key, "")}</div>'
    return f"<div>{hdr}{dsc}{raw}</div>"


def _resolve_grc_period_tables(
    w: dict, *, require_lexicon: "str | None", lexicons: "dict[str, Any]",
    build_paradigm: Any, build_modern: "Any | None",
) -> "list[tuple[str, str]] | None":
    """Resolve *w*'s attested lexicon/period tables. Shared by
    :func:`build_grc_lexicon_tabs` (renders a CSS picker on top) and
    :func:`build_grc_period_tables` (returns the raw list) -- see either
    for the require_lexicon/Modern-rung/error-isolation semantics."""
    _req_table = None
    if require_lexicon is not None:
        _req_backend = lexicons.get(require_lexicon)
        if _req_backend is None:
            return None
        try:
            _req_table = build_paradigm(w, _backend=_req_backend, hide_if_absent=True)
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

    tables = []
    if _req_table:
        tables.append((require_lexicon, _strip_grc_caption(_req_table)))

    # Keep only lexicons whose paradigm actually contains the tested form — no
    # "form absent" tables (build_paradigm_table returns None when hide_if_absent).
    for name, backend in available:
        tbl = build_paradigm(w, _backend=backend, hide_if_absent=True)
        if tbl:
            tables.append((name, _strip_grc_caption(tbl)))

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
        raw = build_paradigm(w, hide_if_absent=True) or ""
        if "unimorph" not in raw:
            return None
        tables.append(("unimorph", _strip_grc_caption(raw)))

    # append the Modern rung last (Epic → … → Roman → Modern), gated by a
    # non-empty Modern paradigm; isolated so a Modern-side failure never breaks
    # the grc dropdown (Gemini R4). Only reached once at least one ancient rung
    # (curated lexicon or unimorph) has already confirmed this exact form.
    if build_modern is not None:
        try:
            m = build_modern(w, hide_if_absent=True)
        except Exception:
            m = None
        if m:
            tables.append(("modern", _strip_grc_caption(m)))

    return tables


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

    def build_lexicon_tabs(w: dict, *, lang: "str | None" = None) -> "str | None":
        tables = _resolve_grc_period_tables(
            w, require_lexicon=require_lexicon, lexicons=lexicons,
            build_paradigm=_build_paradigm, build_modern=_build_modern,
        )
        if tables is None:
            return None

        if len(tables) == 1:
            name = tables[0][0]
            return _wrap_grc_period_html(_GRC_LEX_PERIOD.get(name, name), name, tables[0][1])

        names = [n for n, _ in tables]
        uid = abs(hash(w.get("lemma", "") + w.get("form", ""))) % 99999
        first, others = names[0], names[1:]

        # names[0]'s panel/caption/summary-label default to VISIBLE (not hidden) --
        # every other name's elements default to hidden and only reveal via
        # :checked, as before. This is deliberate, not an oversight: on a fresh
        # render the HTML also marks radio[0] checked (below), which would make a
        # plain "everything hidden, :checked reveals" scheme sufficient on its
        # own -- but re-rendering to a NEW word with FEWER tabs than the previous
        # one can strip every radio's checked state (the browser's own DOM
        # patching preserves live form-control state across same-position
        # elements between renders; a checked radio at a position the new render
        # doesn't have has nowhere to land, and every other position keeps
        # whatever unchecked state it had). Confirmed live via Playwright: select
        # "Modern" for a word with 6 tabs, then click a word with only 5 -- zero
        # radios end up checked and zero panels visible. Defaulting the first
        # tab to visible-unless-overridden self-heals that case without needing
        # JS (mo.Html() doesn't execute inline <script> tags in this codebase).
        hide = ",".join(f"#lp-{uid}-{n},#ld-{uid}-{n},.dc-{uid}-{n}" for n in others)
        show = "".join(
            f"#lr-{uid}-{n}:checked~#lp-{uid}-{n}{{display:block}}"
            f"#lr-{uid}-{n}:checked~#ld-{uid}-{n}{{display:block}}"
            f"#lr-{uid}-{n}:checked~.ddw-{uid} .dc-{uid}-{n}{{display:inline}}"
            for n in names
        )
        # Hide the default (first) tab's elements whenever some OTHER radio is
        # actually checked -- native single radio-group semantics guarantee at
        # most one is ever checked, so this fires only for a genuine user pick.
        hide_default = "".join(
            f"#lr-{uid}-{n}:checked~#lp-{uid}-{first}{{display:none}}"
            f"#lr-{uid}-{n}:checked~#ld-{uid}-{first}{{display:none}}"
            f"#lr-{uid}-{n}:checked~.ddw-{uid} .dc-{uid}-{first}{{display:none}}"
            for n in others
        )
        opt_on = "".join(
            f'#lr-{uid}-{n}:checked~.ddw-{uid} label[for="lr-{uid}-{n}"]'
            "{color:#1e3a8a;font-weight:700;background:#dbeafe}"
            for n in names
        )
        # native <details> handles open/close on click — no focus, no JS; drop the default marker
        nomark = (f".ddw-{uid}>summary{{list-style:none}}"
                  f".ddw-{uid}>summary::-webkit-details-marker{{display:none}}")
        style = f"<style>{hide}{{display:none}}{show}{hide_default}{opt_on}{nomark}</style>"

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


def build_grc_period_tables(
    ag_backend: Any,
    um_backend: Any,
    *,
    lexicons: "dict[str, Any]",
    el_backend: "Any | None" = None,
    lang: str = "ru",
    require_lexicon: "str | None" = None,
) -> Any:
    """Return a ``build_period_tables(w)`` closure -- same lexicon/period
    resolution as :func:`build_grc_lexicon_tabs` (same arguments, same
    ``require_lexicon``/Modern-rung/error-isolation semantics), but returns
    the raw ``[(period_key, table_html), ...]`` list instead of a single
    HTML blob with a CSS-only radio/details picker baked in.

    Use this when you want a real ``mo.ui.dropdown`` for period selection
    (a genuine browser ``<select>``, which correctly closes on pick) rather
    than build_grc_lexicon_tabs's own picker -- pair with
    :func:`grc_period_options` (build the dropdown's ``options=``) and
    :func:`render_grc_period_table` (render the chosen period, in a second
    cell reacting to the dropdown's value). Returns ``None`` when no
    lexicon attests the exact form (same "hide entirely" semantics as
    build_grc_lexicon_tabs).
    """
    _build_paradigm = build_grc_paradigm_table(ag_backend, um_backend, lang=lang)
    _build_modern = (build_modern_paradigm_table(el_backend, lang=lang)
                     if el_backend is not None else None)

    def build_period_tables(w: dict) -> "list[tuple[str, str]] | None":
        return _resolve_grc_period_tables(
            w, require_lexicon=require_lexicon, lexicons=lexicons,
            build_paradigm=_build_paradigm, build_modern=_build_modern,
        )

    return build_period_tables


def grc_period_options(tables: "list[tuple[str, str]]") -> "dict[str, str]":
    """Display-label -> period-key options for a real
    ``mo.ui.dropdown(options=grc_period_options(tables), ...)``, from
    :func:`build_grc_period_tables`'s ``tables`` result. Uses the same
    full ``_GRC_LEX_PERIOD`` name/dates as :func:`build_grc_lexicon_tabs`'s
    own CSS picker did for its summary pill and menu options."""
    return {_GRC_LEX_PERIOD.get(n, n): n for n, _ in tables}


def render_grc_period_table(tables: "list[tuple[str, str]]", period: "str | None" = None) -> str:
    """Render one period's description + table from *tables* (a
    :func:`build_grc_period_tables` result); includes the name/dates header
    too when there's no dropdown to show it (a single attested period).
    *period* is a period key (a real ``mo.ui.dropdown``'s ``.value``, built
    from :func:`grc_period_options`); falls back to *tables*' first entry
    when *period* is ``None`` or not present in *tables*."""
    if not tables:
        return ""
    _by_key = dict(tables)
    if period not in _by_key:
        period = tables[0][0]
    if len(tables) > 1:
        # negative margin cancels marimo's own gap to the dropdown's cell above
        dsc = f'<div style="{_GRC_PERIOD_DESC_STYLE};margin-top:-20px">{_GRC_LEX_DESCR.get(period, "")}</div>'
        return f"<div>{dsc}{_by_key[period]}</div>"
    return _wrap_grc_period_html(_GRC_LEX_PERIOD.get(period, period), period, _by_key[period])


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
    from eee_project.notebook_utils import LEXICON_TAG_POS, LEXICON_TAG_POS_ALIASES
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
