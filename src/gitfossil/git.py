"""Small, dependency-free adapter around the Git command line."""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


class GitError(RuntimeError):
    """Raised when Git cannot inspect the requested repository."""


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int = 0
    deleted: int = 0
    binary: bool = False


@dataclass
class Commit:
    sha: str
    author_name: str
    author_email: str
    authored_at: datetime
    subject: str
    files: List[FileChange] = field(default_factory=list)


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    """Run Git in *repo* without invoking a shell."""

    command = ["git", "-C", str(repo), *args]
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise GitError("Git is not installed or is not available on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError("Git took too long to read this repository.") from exc

    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise GitError(detail)
    return result.stdout


def discover_repository(path: Path) -> Path:
    """Resolve *path* to the top level of a Git work tree."""

    candidate = path.expanduser().resolve()
    if not candidate.exists():
        raise GitError(f"Path does not exist: {candidate}")
    try:
        root = run_git(candidate, "rev-parse", "--show-toplevel").strip()
    except GitError as exc:
        raise GitError(f"Not a Git repository: {candidate}") from exc
    if not root:
        raise GitError(f"Not a Git work tree: {candidate}")
    return Path(root).resolve()


def repository_metadata(repo: Path) -> dict:
    """Return non-sensitive metadata used in the report."""

    branch = run_git(repo, "branch", "--show-current", check=False).strip() or "detached"
    head = run_git(repo, "rev-parse", "--short", "HEAD", check=False).strip()
    return {
        "name": repo.name,
        "branch": branch,
        "head": head,
    }


def collect_commits(
    repo: Path,
    *,
    max_commits: int = 5000,
    since: Optional[str] = None,
    all_refs: bool = False,
    include_merges: bool = False,
) -> List[Commit]:
    """Read commit metadata and numstat changes in a single Git process."""

    if max_commits < 1:
        raise ValueError("max_commits must be positive")

    args = [
        "log",
        "--no-color",
        "--numstat",
        "--find-renames=40%",
        "-n",
        str(max_commits),
        "--date=iso-strict",
        "--format=%x1e%H%x1f%aN%x1f%aE%x1f%aI%x1f%s",
    ]
    if all_refs:
        args.append("--all")
    else:
        args.append("HEAD")
    if since:
        args.extend(["--since", since])
    if not include_merges:
        args.append("--no-merges")

    output = run_git(repo, *args, check=False)
    if not output.strip():
        return []

    commits: List[Commit] = []
    for chunk in output.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk or "\x1f" not in chunk:
            continue
        lines = chunk.splitlines()
        header = lines[0].split("\x1f", 4)
        if len(header) != 5:
            continue
        try:
            authored_at = datetime.fromisoformat(header[3].replace("Z", "+00:00"))
        except ValueError:
            continue

        commit = Commit(
            sha=header[0],
            author_name=header[1] or "Unknown",
            author_email=header[2].lower(),
            authored_at=authored_at,
            subject=header[4],
        )
        seen_paths = set()
        for line in lines[1:]:
            change = _parse_numstat_line(line)
            if change is None or change.path in seen_paths:
                continue
            seen_paths.add(change.path)
            commit.files.append(change)
        if commit.files:
            commits.append(commit)
    return commits


def _parse_numstat_line(line: str) -> Optional[FileChange]:
    parts = line.split("\t", 2)
    if len(parts) != 3:
        return None
    added_raw, deleted_raw, raw_path = parts
    path = _normalize_rename(raw_path)
    if not path or path.startswith(".git/"):
        return None
    binary = added_raw == "-" or deleted_raw == "-"
    try:
        added = 0 if binary else max(0, int(added_raw))
        deleted = 0 if binary else max(0, int(deleted_raw))
    except ValueError:
        return None
    return FileChange(path=path, added=added, deleted=deleted, binary=binary)


def _normalize_rename(path: str) -> str:
    """Use the destination side of Git's compact rename notation."""

    path = path.strip()
    if " => " not in path:
        return path
    if "{" in path and "}" in path:
        prefix, body = path.split("{", 1)
        body, suffix = body.split("}", 1)
        _, _, destination = body.partition(" => ")
        compact = f"{prefix}{destination}{suffix}"
        return compact.replace("//", "/").replace("  ", " ")
    _, _, destination = path.partition(" => ")
    return destination.strip()


def is_excluded(path: str, patterns: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def filter_commits(
    commits: Iterable[Commit],
    exclude_patterns: Sequence[str] = (),
) -> List[Commit]:
    """Remove excluded paths while retaining commits with other changes."""

    if not exclude_patterns:
        return list(commits)
    filtered: List[Commit] = []
    for commit in commits:
        files = [
            change
            for change in commit.files
            if not is_excluded(change.path, exclude_patterns)
        ]
        if files:
            filtered.append(
                Commit(
                    sha=commit.sha,
                    author_name=commit.author_name,
                    author_email=commit.author_email,
                    authored_at=commit.authored_at,
                    subject=commit.subject,
                    files=files,
                )
            )
    return filtered
