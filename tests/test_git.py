from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gitfossil.git import (
    GitError,
    collect_commits,
    discover_repository,
    filter_commits,
)
from tests.helpers import TemporaryRepository


class GitIntegrationTests(unittest.TestCase):
    def test_collects_real_commit_history(self) -> None:
        with TemporaryRepository() as repo:
            repo.write("src/app.py", "print('one')\n")
            repo.commit("Initial app")
            repo.write("src/app.py", "print('two')\nprint('more')\n")
            repo.write("docs/readme.md", "# Docs\n")
            repo.commit("Add docs")

            discovered = discover_repository(repo.path)
            commits = collect_commits(discovered)

        self.assertEqual(discovered, repo.path.resolve())
        self.assertEqual(len(commits), 2)
        self.assertEqual({change.path for change in commits[0].files}, {"src/app.py", "docs/readme.md"})
        self.assertEqual(commits[0].author_email, "ada@example.test")

    def test_tracks_renames_as_destination_path(self) -> None:
        with TemporaryRepository() as repo:
            repo.write("old/name.py", "line one\nline two\n" * 10)
            repo.commit("Initial")
            (repo.path / "new").mkdir()
            repo.git("mv", "old/name.py", "new/name.py")
            repo.commit("Move file")

            commits = collect_commits(repo.path)

        self.assertTrue(any(change.path == "new/name.py" for change in commits[0].files))
        self.assertFalse(any("=>" in change.path for change in commits[0].files))

    def test_filter_keeps_commit_when_other_files_remain(self) -> None:
        with TemporaryRepository() as repo:
            repo.write("src/app.py", "app\n")
            repo.write("package-lock.json", "{}\n")
            repo.commit("Initial")
            commits = collect_commits(repo.path)
            filtered = filter_commits(commits, ["*.lock", "package-lock.json"])
            only_generated = filter_commits(commits, ["*.py", "*.json"])

        self.assertEqual(len(filtered), 1)
        self.assertEqual([change.path for change in filtered[0].files], ["src/app.py"])
        self.assertEqual(only_generated, [])

    def test_invalid_repository_raises_friendly_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(GitError, "Not a Git repository"):
                discover_repository(Path(directory))

    def test_since_filter_and_commit_limit(self) -> None:
        with TemporaryRepository() as repo:
            repo.write("a.txt", "one\n")
            repo.commit("First")
            repo.write("a.txt", "two\n")
            repo.commit("Second")
            commits = collect_commits(repo.path, max_commits=1)

        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].subject, "Second")


if __name__ == "__main__":
    unittest.main()
