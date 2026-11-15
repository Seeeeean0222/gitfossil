from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class TemporaryRepository:
    def __init__(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Ada Tester")
        self.git("config", "user.email", "ada@example.test")

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.path), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout

    def write(self, relative_path: str, content: str) -> Path:
        target = self.path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def commit(self, message: str, name: str = "Ada Tester", email: str = "ada@example.test") -> str:
        self.git("add", "-A")
        self.git(
            "-c",
            f"user.name={name}",
            "-c",
            f"user.email={email}",
            "commit",
            "-q",
            "-m",
            message,
        )
        return self.git("rev-parse", "HEAD").strip()

    def close(self) -> None:
        self._temp.cleanup()

    def __enter__(self) -> "TemporaryRepository":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
