#!/usr/bin/env python3
"""Build the deterministic GitHub Pages demo without touching a Git repository."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gitfossil.analysis import analyze_history  # noqa: E402
from gitfossil.git import Commit, FileChange  # noqa: E402
from gitfossil.renderer import render_report  # noqa: E402


CONTRIBUTORS = [
    ("Maya Chen", "maya@example.test"),
    ("Jon Bell", "jon@example.test"),
    ("Priya Shah", "priya@example.test"),
    ("Sam Okafor", "sam@example.test"),
]

SCENARIOS = [
    [("src/api/users.py", 28, 9), ("db/schema.sql", 12, 4)],
    [("src/api/users.py", 17, 3), ("web/profile.tsx", 38, 14)],
    [("billing/planner.py", 45, 16), ("billing/test_planner.py", 21, 5)],
    [("infra/deploy.yml", 8, 5), ("config/regions.toml", 15, 8)],
    [("web/profile.tsx", 25, 9), ("web/design_tokens.css", 12, 2)],
    [("billing/planner.py", 30, 18), ("db/schema.sql", 6, 2)],
    [("src/jobs/reconcile.py", 22, 22), ("infra/deploy.yml", 4, 3)],
    [("docs/onboarding.md", 34, 3), ("src/api/users.py", 9, 2)],
]


def build_history() -> list[Commit]:
    commits = []
    start = datetime(2025, 1, 8, 10, 0, tzinfo=timezone.utc)
    for index in range(64):
        author_index = (index + index // 7) % len(CONTRIBUTORS)
        name, email = CONTRIBUTORS[author_index]
        scenario = SCENARIOS[index % len(SCENARIOS)]
        # Concentrate the oldest critical module around its original owner.
        if index % 4 == 0:
            name, email = CONTRIBUTORS[2]
        files = [
            FileChange(
                path=path,
                added=max(1, added + (index % 9) * 2),
                deleted=max(0, deleted + (index % 5)),
            )
            for path, added, deleted in scenario
        ]
        commits.append(
            Commit(
                sha=f"{index + 1:040x}",
                author_name=name,
                author_email=email,
                authored_at=start + timedelta(days=index * 9, hours=index % 6),
                subject=f"Evolution step {index + 1}",
                files=files,
            )
        )
    return commits


def main() -> None:
    report = analyze_history(
        build_history(),
        {"name": "meridian-commerce", "branch": "main", "head": "8f31c2a"},
        generated_at=datetime(2026, 9, 2, 8, 0, tzinfo=timezone.utc),
    )
    report["repository"]["root"] = "local/demo-workspace"
    report["repository"]["filters"] = {
        "max_commits": 5000,
        "since": "",
        "all_refs": False,
        "include_merges": False,
        "excludes": ["*.lock", "dist/*"],
    }
    destination = ROOT / "docs" / "index.html"
    destination.write_text(render_report(report), encoding="utf-8")
    print(f"Built {destination.relative_to(ROOT)} from {len(report['files'])} file fossils")


if __name__ == "__main__":
    main()
