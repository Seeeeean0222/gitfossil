from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gitfossil.cli import main
from tests.helpers import TemporaryRepository


class CliIntegrationTests(unittest.TestCase):
    def test_scan_writes_self_contained_html_and_json(self) -> None:
        with TemporaryRepository() as repo, tempfile.TemporaryDirectory() as output:
            repo.write("src/main.py", "def start():\n    return 1\n")
            repo.commit("Initial")
            repo.write("src/main.py", "def start():\n    return 2\n")
            repo.commit("Update result")
            html_path = Path(output) / "report.html"
            json_path = Path(output) / "report.json"

            status = main(
                [
                    "scan",
                    str(repo.path),
                    "--output",
                    str(html_path),
                    "--json",
                    str(json_path),
                    "--quiet",
                ]
            )
            html = html_path.read_text(encoding="utf-8")
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 0)
        self.assertIn("<!doctype html>", html)
        self.assertIn('id="report-data"', html)
        self.assertNotIn("https://cdn", html)
        self.assertEqual(payload["repository"]["commit_count"], 2)
        self.assertEqual(payload["files"][0]["path"], "src/main.py")

    def test_excluded_files_do_not_create_empty_commits(self) -> None:
        with TemporaryRepository() as repo, tempfile.TemporaryDirectory() as output:
            repo.write("keep.py", "value = 1\n")
            repo.write("generated.json", "{}\n")
            repo.commit("Initial")
            repo.write("generated.json", '{"value": 2}\n')
            repo.commit("Generated only")
            json_path = Path(output) / "report.json"

            status = main(
                [
                    "scan",
                    str(repo.path),
                    "-o",
                    str(Path(output) / "report.html"),
                    "--json",
                    str(json_path),
                    "--exclude",
                    "*.json",
                    "--quiet",
                ]
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 0)
        self.assertEqual(payload["repository"]["commit_count"], 1)
        self.assertEqual([item["path"] for item in payload["files"]], ["keep.py"])

    def test_not_a_repository_returns_error_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            status = main(["scan", directory, "--quiet"])
        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
