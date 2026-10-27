"""Every public name of eee_project is documented in the README or in a docs/*.md file."""
import re
from pathlib import Path

import eee_project

ROOT = Path(__file__).parent.parent
DOCS = "\n".join(p.read_text(encoding="utf-8") for p in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))])


def test_every_public_name_is_documented():
    missing = [n for n in eee_project.__all__ if not re.search(rf"\b{re.escape(n)}\b", DOCS)]
    assert not missing, f"public names found in no doc: {missing}"
