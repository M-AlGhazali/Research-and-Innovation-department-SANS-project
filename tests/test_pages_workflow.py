"""The Pages workflow copies Map 2 file by file: every local module and stylesheet the page loads must be in that list."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_map2_file_the_page_loads_is_published():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    published = set(re.findall(r"map-2/([\w.-]+\.(?:mjs|js|css))\b", workflow))
    missing = []
    for name in sorted(published):
        if name.endswith((".mjs", ".js")):
            source = (ROOT / "map-2" / name).read_text(encoding="utf-8")
            missing += [f"{name} imports {dep}" for dep in re.findall(r"from\s*['\"]\./([\w.-]+\.m?js)\b", source) if dep not in published]
    html = (ROOT / "map-2/index.html").read_text(encoding="utf-8")
    missing += [f"index.html loads {dep}" for dep in re.findall(r"(?:src|href)=\"([\w.-]+\.(?:m?js|css))\b", html) if dep not in published]
    assert not missing, "Add to .github/workflows/pages.yml: " + "; ".join(missing)
