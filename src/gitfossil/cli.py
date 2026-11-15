"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import __version__
from .analysis import analyze_history
from .git import (
    GitError,
    collect_commits,
    discover_repository,
    filter_commits,
    repository_metadata,
)
from .renderer import render_report


DEFAULT_EXCLUDES = [
    "*.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.snap",
    "vendor/*",
    "node_modules/*",
    "dist/*",
    "build/*",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitfossil",
        description="Turn a Git repository's history into an engineering risk map.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Analyze a repository and build an HTML report.")
    scan.add_argument("path", nargs="?", default=".", help="Repository path (default: current directory)")
    scan.add_argument("-o", "--output", default="gitfossil-report.html", help="HTML output path")
    scan.add_argument("--json", dest="json_output", help="Optional machine-readable JSON output")
    scan.add_argument("--max-commits", type=int, default=5000, help="Maximum sampled commits")
    scan.add_argument("--since", help='Only inspect commits since a Git date, e.g. "12 months ago"')
    scan.add_argument("--all-refs", action="store_true", help="Include all reachable refs")
    scan.add_argument("--include-merges", action="store_true", help="Include merge commits")
    scan.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob of paths to ignore; repeat for multiple patterns",
    )
    scan.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="Keep lockfiles, generated assets and dependency folders",
    )
    scan.add_argument("--quiet", action="store_true", help="Suppress the summary in the terminal")
    return parser


def scan_repository(args: argparse.Namespace) -> dict:
    repo = discover_repository(Path(args.path))
    commits = collect_commits(
        repo,
        max_commits=args.max_commits,
        since=args.since,
        all_refs=args.all_refs,
        include_merges=args.include_merges,
    )
    excludes = ([] if args.no_default_excludes else DEFAULT_EXCLUDES) + args.exclude
    commits = filter_commits(commits, excludes)
    report = analyze_history(
        commits,
        repository_metadata(repo),
        generated_at=datetime.now(timezone.utc),
    )
    report["repository"]["root"] = str(repo)
    report["repository"]["filters"] = {
        "max_commits": args.max_commits,
        "since": args.since or "",
        "all_refs": args.all_refs,
        "include_merges": args.include_merges,
        "excludes": excludes,
    }
    return report


def write_outputs(report: dict, html_path: Path, json_path: Optional[Path]) -> None:
    html_path = html_path.expanduser().resolve()
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_report(report), encoding="utf-8")
    if json_path:
        resolved_json = json_path.expanduser().resolve()
        resolved_json.parent.mkdir(parents=True, exist_ok=True)
        resolved_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def print_summary(report: dict, html_path: Path) -> None:
    summary = report["summary"]
    repository = report["repository"]
    print(f"GitFossil {__version__} · {repository['name']}")
    print(
        f"Scanned {repository['commit_count']} commits · "
        f"{summary['files_analyzed']} files · "
        f"{repository['author_count']} contributors"
    )
    print(
        f"Health {summary['health_score']}/100 · "
        f"{summary['hotspots']} hotspots · "
        f"{summary['knowledge_silos']} silos · "
        f"{summary['coupling_links']} coupling links"
    )
    print(f"Report: {html_path.expanduser().resolve()}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            report = scan_repository(args)
            html_path = Path(args.output)
            json_path = Path(args.json_output) if args.json_output else None
            write_outputs(report, html_path, json_path)
            if not args.quiet:
                print_summary(report, html_path)
            return 0
    except (GitError, OSError, ValueError) as exc:
        print(f"gitfossil: {exc}", file=sys.stderr)
        return 2
    parser.error("Unknown command")
    return 2
