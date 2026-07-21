# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.13",
#     "eee-project @ git+https://codeberg.org/EEE-project/eee-project.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee-project.git" }
# ///
"""ConfigStore demo — navigation config storage for molab notebooks.

Shows from_url (molab pattern) and from_file / from_dict (local dev).

Run locally:
    uv run marimo edit examples/config_store_notebook.py --no-token

Upload to molab to test from_url against a live Codeberg raw URL.
"""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(cfg, eee_topbar, mo):
    eee_topbar(
        mo,
        back_url=cfg.index_url(),
        lang="en",
        titles="ConfigStore Demo",
        style="index",
        icon="📚",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # ConfigStore demo

    `ConfigStore` manages lesson navigation config and GA settings with a
    pluggable source — fetch from URL for molab, read files for local dev.

    ## `from_url` — molab pattern

    Fetch `lessons.tsv` per-course and `ga.json` from the repo root:

    ```python
    _ROOT = "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main"
    _cfg = ConfigStore.from_url(
        f"{_ROOT}/palaestra/ancient_greek.2026.summer/lessons.tsv",
        ga=f"{_ROOT}/ga.json",
    )
    ```
    """)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Lessons
    """)
    return


@app.cell
def _(cfg, mo):
    mo.ui.table(cfg.lessons())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Accessors
    """)
    return


@app.cell
def _(cfg, mo):
    mo.md(f"""
    | Accessor | Value |
    |---|---|
    | `cfg.index_url()` | `{cfg.index_url()}` |
    | `cfg.ga_config()` | `{cfg.ga_config()}` |
    | `len(cfg.lessons())` | `{len(cfg.lessons())}` |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## `from_file` — local dev pattern

    When running from a local checkout with sidecar files next to the notebook:

    ```python
    _cfg = ConfigStore.from_file(__file__)
    # reads lessons.tsv + ga.json from the same directory (or one level up)
    ```

    `lessons.tsv` (tab-separated, same columns as above):

    ```
    url             icon  greek        label       title      desc            index_url
    https://...     Α     Μάθημα α'   Lesson 1    Alphabet   Letters         https://...
    ```

    `ga.json`:
    ```json
    {"measurement_id": "G-XXXXXXXXXX"}
    ```
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    from eee_project import ConfigStore, eee_topbar

    _ROOT = "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main"
    cfg = ConfigStore.from_url(
        f"{_ROOT}/palaestra/ancient_greek.2026.summer/lessons.tsv",
        ga=f"{_ROOT}/ga.json",
    )

    return cfg, eee_topbar, mo


if __name__ == "__main__":
    app.run()
