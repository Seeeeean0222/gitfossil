"""Render a self-contained, offline HTML report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def render_report(report: dict, template_path: Optional[Path] = None) -> str:
    template = template_path or Path(__file__).with_name("template.html")
    source = template.read_text(encoding="utf-8")
    # Escaping "<" prevents repository content from closing the script element.
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    if "__REPORT_JSON__" not in source:
        raise ValueError("The HTML template is missing the __REPORT_JSON__ marker.")
    return source.replace("__REPORT_JSON__", payload)
