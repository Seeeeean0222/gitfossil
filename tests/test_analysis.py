from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from gitfossil.analysis import analyze_history
from gitfossil.git import Commit, FileChange


def commit(
    day: int,
    name: str,
    files: list[str],
    *,
    added: int = 10,
    deleted: int = 2,
) -> Commit:
    return Commit(
        sha=f"{day:040x}",
        author_name=name,
        author_email=f"{name.lower()}@example.test",
        authored_at=datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=day),
        subject=f"Change {day}",
        files=[FileChange(path, added, deleted) for path in files],
    )


class AnalysisTests(unittest.TestCase):
    def test_empty_history_returns_actionable_empty_report(self) -> None:
        report = analyze_history(
            [],
            {"name": "empty", "branch": "main", "head": ""},
            generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(report["summary"]["files_analyzed"], 0)
        self.assertEqual(report["summary"]["health_score"], 100)
        self.assertEqual(report["files"], [])
        self.assertIn("No history found", report["insights"][0]["title"])

    def test_single_owner_is_detected_as_knowledge_silo(self) -> None:
        commits = [commit(index, "Ada", ["src/core.py"]) for index in range(4)]
        report = analyze_history(
            commits,
            {"name": "demo", "branch": "main", "head": "abc"},
            generated_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
        )
        target = report["files"][0]
        self.assertEqual(target["top_owner"], "Ada")
        self.assertEqual(target["top_share"], 1.0)
        self.assertEqual(target["bus_factor"], 1)
        self.assertIn("knowledge silo", target["reasons"])
        self.assertEqual(report["summary"]["knowledge_silos"], 1)
        self.assertEqual(report["summary"]["overall_bus_factor"], 1)

    def test_cross_directory_cochange_becomes_hidden_dependency(self) -> None:
        commits = [
            commit(0, "Ada", ["api/users.py", "db/schema.sql"]),
            commit(1, "Lin", ["api/users.py", "db/schema.sql"]),
            commit(2, "Ada", ["api/users.py", "db/schema.sql"]),
            commit(3, "Lin", ["unrelated/readme.md"]),
            commit(4, "Ada", ["unrelated/test.py"]),
            commit(5, "Lin", ["unrelated/config.toml"]),
        ]
        report = analyze_history(
            commits,
            {"name": "demo", "branch": "main", "head": "abc"},
            generated_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
        )
        self.assertTrue(report["coupling"])
        pair = report["coupling"][0]
        self.assertEqual({pair["left"], pair["right"]}, {"api/users.py", "db/schema.sql"})
        self.assertTrue(pair["cross_directory"])
        self.assertEqual(pair["kind"], "hidden dependency")
        self.assertEqual(pair["cochanges"], 3)

    def test_bulk_commit_is_ignored_for_coupling(self) -> None:
        files = [f"src/file_{index}.py" for index in range(45)]
        commits = [commit(0, "Ada", files), commit(1, "Ada", files)]
        report = analyze_history(
            commits,
            {"name": "demo", "branch": "main", "head": "abc"},
            generated_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
            max_files_per_commit=40,
        )
        self.assertEqual(report["coupling"], [])

    def test_timeline_and_contributors_are_aggregated(self) -> None:
        commits = [
            commit(0, "Ada", ["src/a.py"], added=20, deleted=3),
            commit(1, "Lin", ["src/b.py"], added=7, deleted=9),
            commit(40, "Ada", ["src/a.py"], added=5, deleted=5),
        ]
        report = analyze_history(
            commits,
            {"name": "demo", "branch": "main", "head": "abc"},
            generated_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(len(report["timeline"]), 2)
        self.assertEqual(report["timeline"][0]["commits"], 2)
        self.assertEqual(report["contributors"][0]["name"], "Ada")
        self.assertEqual(report["contributors"][0]["commits"], 2)
        self.assertEqual(report["summary"]["total_additions"], 32)
        self.assertEqual(report["summary"]["total_deletions"], 17)

    def test_email_identity_merges_display_name_variants(self) -> None:
        first = commit(0, "Ada", ["src/a.py"])
        second = commit(1, "A. Lovelace", ["src/a.py"])
        second.author_email = first.author_email
        report = analyze_history(
            [first, second],
            {"name": "demo", "branch": "main", "head": "abc"},
            generated_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(report["repository"]["author_count"], 1)
        self.assertEqual(report["summary"]["overall_bus_factor"], 1)


if __name__ == "__main__":
    unittest.main()
