"""Explainable repository risk and coupling metrics."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .git import Commit


def analyze_history(
    commits: Sequence[Commit],
    repository: dict,
    *,
    generated_at: Optional[datetime] = None,
    max_files_per_commit: int = 40,
) -> dict:
    """Build a serializable report from a chronological-independent commit list."""

    now = generated_at or datetime.now(timezone.utc)
    ordered = sorted(commits, key=lambda item: item.authored_at)
    generated_iso = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {
        **repository,
        "generated_at": generated_iso,
        "commit_count": len(ordered),
        "author_count": len({_identity(commit) for commit in ordered}),
        "first_commit": _iso(ordered[0]) if ordered else "",
        "last_commit": _iso(ordered[-1]) if ordered else "",
    }

    if not ordered:
        return _empty_report(metadata)

    file_states: Dict[str, dict] = {}
    author_commits: Counter = Counter()
    author_names: Dict[str, Counter] = defaultdict(Counter)
    author_additions: Counter = Counter()
    author_deletions: Counter = Counter()
    month_states: Dict[str, dict] = defaultdict(
        lambda: {"commits": 0, "additions": 0, "deletions": 0, "authors": set()}
    )

    for commit in ordered:
        identity = _identity(commit)
        author_commits[identity] += 1
        author_names[identity][commit.author_name] += 1
        month = commit.authored_at.strftime("%Y-%m")
        month_states[month]["commits"] += 1
        month_states[month]["authors"].add(identity)

        for change in commit.files:
            state = file_states.setdefault(
                change.path,
                {
                    "path": change.path,
                    "commits": 0,
                    "additions": 0,
                    "deletions": 0,
                    "authors": Counter(),
                    "last_at": commit.authored_at,
                    "first_at": commit.authored_at,
                    "transitions": 0,
                    "last_author": None,
                    "binary_commits": 0,
                },
            )
            state["commits"] += 1
            state["additions"] += change.added
            state["deletions"] += change.deleted
            state["authors"][identity] += 1
            state["last_at"] = max(state["last_at"], commit.authored_at)
            state["first_at"] = min(state["first_at"], commit.authored_at)
            if change.binary:
                state["binary_commits"] += 1
            if state["last_author"] and state["last_author"] != identity:
                state["transitions"] += 1
            state["last_author"] = identity
            author_additions[identity] += change.added
            author_deletions[identity] += change.deleted
            month_states[month]["additions"] += change.added
            month_states[month]["deletions"] += change.deleted

    max_file_commits = max(state["commits"] for state in file_states.values())
    max_churn = max(
        state["additions"] + state["deletions"] for state in file_states.values()
    )
    first_time = ordered[0].authored_at
    total_span_days = max(1.0, (ordered[-1].authored_at - first_time).total_seconds() / 86400)

    files = []
    for state in file_states.values():
        author_total = sum(state["authors"].values())
        ranked_authors = state["authors"].most_common()
        top_share = ranked_authors[0][1] / author_total if author_total else 0
        bus_factor = _bus_factor([weight for _, weight in ranked_authors], threshold=0.8)
        churn = state["additions"] + state["deletions"]
        age_days = max(0.0, (ordered[-1].authored_at - state["last_at"]).total_seconds() / 86400)
        recency = min(1.0, age_days / total_span_days)
        rewrite = state["deletions"] / churn if churn else 0.0

        frequency_risk = math.log1p(state["commits"]) / max(1e-9, math.log1p(max_file_commits))
        churn_risk = math.log1p(churn) / max(1e-9, math.log1p(max_churn))
        ownership_risk = max(0.0, (top_share - 0.5) / 0.5)
        bus_risk = max(0.0, 1.0 - (bus_factor / min(3, max(1, len(ranked_authors)))))
        risk = 100 * (
            0.32 * frequency_risk
            + 0.23 * churn_risk
            + 0.23 * ownership_risk
            + 0.12 * bus_risk
            + 0.10 * recency
        )
        risk = round(min(100.0, max(0.0, risk)), 1)

        reasons = []
        if frequency_risk >= 0.7:
            reasons.append("frequent changes")
        if churn_risk >= 0.7:
            reasons.append("high churn")
        if top_share >= 0.75 and state["commits"] >= 3:
            reasons.append("knowledge silo")
        if state["transitions"] >= 4:
            reasons.append("ownership handoffs")
        if rewrite >= 0.6 and churn >= 50:
            reasons.append("rewrite-heavy")
        if recency >= 0.65:
            reasons.append("aging hotspot")

        files.append(
            {
                "path": state["path"],
                "commits": state["commits"],
                "additions": state["additions"],
                "deletions": state["deletions"],
                "churn": churn,
                "risk": risk,
                "top_owner": _display_name(state["authors"], author_names),
                "top_share": round(top_share, 3),
                "bus_factor": bus_factor,
                "handoffs": state["transitions"],
                "last_touched": _iso_time(state["last_at"]),
                "age_days": round(age_days),
                "authors": {
                    _display_name_identity(identity, author_names): count
                    for identity, count in ranked_authors
                },
                "reasons": reasons,
            }
        )

    files.sort(key=lambda item: (-item["risk"], -item["commits"], item["path"]))
    coupling = _analyze_coupling(ordered, max_files_per_commit=max_files_per_commit)
    contributors = _contributor_rows(
        author_commits, author_names, author_additions, author_deletions
    )
    timeline = _timeline_rows(month_states)
    overall_bus_factor = _bus_factor(list(author_commits.values()), threshold=0.8)
    silo_count = sum(
        1
        for item in files
        if item["top_share"] >= 0.75 and item["commits"] >= 3
    )
    hotspot_count = sum(1 for item in files if item["risk"] >= 45)
    fragility = round(
        sum(item["risk"] for item in files[: min(10, len(files))])
        / max(1, min(10, len(files))),
        1,
    )

    summary = {
        "fragility_index": fragility,
        "health_score": round(100 - fragility, 1),
        "files_analyzed": len(files),
        "hotspots": hotspot_count,
        "knowledge_silos": silo_count,
        "coupling_links": len(coupling),
        "overall_bus_factor": overall_bus_factor,
        "total_additions": sum(item["additions"] for item in files),
        "total_deletions": sum(item["deletions"] for item in files),
    }

    insights = _build_insights(summary, files, coupling, contributors)
    return {
        "schema_version": 1,
        "repository": metadata,
        "summary": summary,
        "insights": insights,
        "files": files,
        "coupling": coupling[:40],
        "contributors": contributors,
        "timeline": timeline,
    }


def _analyze_coupling(
    commits: Sequence[Commit], *, max_files_per_commit: int
) -> List[dict]:
    pair_counts: Counter = Counter()
    file_counts: Counter = Counter()
    eligible = 0

    for commit in commits:
        paths = sorted({change.path for change in commit.files})
        if len(paths) < 2 or len(paths) > max_files_per_commit:
            continue
        eligible += 1
        for path in paths:
            file_counts[path] += 1
        for left_index, left in enumerate(paths):
            for right in paths[left_index + 1 :]:
                pair_counts[(left, right)] += 1

    rows = []
    for (left, right), cochanges in pair_counts.items():
        if cochanges < 2 or eligible == 0:
            continue
        left_count = file_counts[left]
        right_count = file_counts[right]
        confidence = cochanges / min(left_count, right_count)
        support = cochanges / eligible
        lift = (cochanges * eligible) / max(1, left_count * right_count)
        if confidence < 0.35 or support < 0.015:
            continue
        cross_directory = _dirname(left) != _dirname(right)
        score = (
            34 * confidence
            + 26 * min(1.0, lift / 3)
            + 22 * min(1.0, cochanges / 5)
            + 18 * (1.0 if cross_directory else 0.35)
        )
        rows.append(
            {
                "left": left,
                "right": right,
                "cochanges": cochanges,
                "confidence": round(confidence, 3),
                "support": round(support, 3),
                "lift": round(lift, 2),
                "cross_directory": cross_directory,
                "score": round(score, 1),
                "kind": "hidden dependency" if cross_directory else "local cluster",
            }
        )
    rows.sort(key=lambda item: (-item["score"], -item["cochanges"], item["left"]))
    return rows


def _contributor_rows(
    commit_counts: Counter,
    names: Dict[str, Counter],
    additions: Counter,
    deletions: Counter,
) -> List[dict]:
    total = sum(commit_counts.values())
    rows = []
    for identity, count in commit_counts.most_common():
        display = _display_name_identity(identity, names)
        rows.append(
            {
                "name": display,
                "commits": count,
                "share": round(count / max(1, total), 3),
                "additions": additions[identity],
                "deletions": deletions[identity],
            }
        )
    return rows


def _timeline_rows(states: Dict[str, dict]) -> List[dict]:
    return [
        {
            "month": month,
            "commits": state["commits"],
            "additions": state["additions"],
            "deletions": state["deletions"],
            "authors": len(state["authors"]),
        }
        for month, state in sorted(states.items())
    ]


def _build_insights(
    summary: dict, files: List[dict], coupling: List[dict], contributors: List[dict]
) -> List[dict]:
    insights = []
    if files:
        top = files[0]
        severity = "high" if top["risk"] >= 50 else "medium"
        insights.append(
            {
                "severity": severity,
                "title": f"Start review at {top['path']}",
                "detail": (
                    f"Its risk score is {top['risk']}/100 across {top['commits']} commits. "
                    f"{top['top_owner']} owns {round(top['top_share'] * 100)}% of changes."
                ),
            }
        )
    if summary["knowledge_silos"]:
        insights.append(
            {
                "severity": "high" if summary["knowledge_silos"] >= 3 else "medium",
                "title": f"{summary['knowledge_silos']} likely knowledge silos",
                "detail": "At least 75% of changes belong to one contributor. Pair on the riskiest file before it becomes critical.",
            }
        )
    if coupling:
        first = coupling[0]
        insights.append(
            {
                "severity": "medium",
                "title": "A likely hidden dependency surfaced",
                "detail": (
                    f"{first['left']} and {first['right']} changed together "
                    f"{first['cochanges']} times ({round(first['confidence'] * 100)}% confidence)."
                ),
            }
        )
    if contributors:
        leader = contributors[0]
        insights.append(
            {
                "severity": "medium" if leader["share"] >= 0.7 and len(contributors) > 1 else "low",
                "title": f"Bus factor is {summary['overall_bus_factor']}",
                "detail": (
                    f"{leader['name']} authored {round(leader['share'] * 100)}% of sampled commits. "
                    "A healthy bus factor is at least two."
                ),
            }
        )
    return insights


def _bus_factor(weights: Iterable[int], threshold: float = 0.8) -> int:
    values = sorted((value for value in weights if value > 0), reverse=True)
    total = sum(values)
    if total == 0:
        return 0
    running = 0
    for index, value in enumerate(values, start=1):
        running += value
        if running / total >= threshold:
            return index
    return len(values)


def _display_name(authors: Counter, names: Dict[str, Counter]) -> str:
    if not authors:
        return "Unknown"
    identity = authors.most_common(1)[0][0]
    return _display_name_identity(identity, names)


def _display_name_identity(identity: str, names: Dict[str, Counter]) -> str:
    values = names.get(identity)
    if values:
        return values.most_common(1)[0][0]
    return identity.split("@", 1)[0].replace(".", " ").title()


def _identity(commit: Commit) -> str:
    return commit.author_email or commit.author_name.lower()


def _dirname(path: str) -> str:
    return str(PurePosixPath(path).parent)


def _iso(commit: Commit) -> str:
    return _iso_time(commit.authored_at)


def _iso_time(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _empty_report(metadata: dict) -> dict:
    return {
        "schema_version": 1,
        "repository": metadata,
        "summary": {
            "fragility_index": 0,
            "health_score": 100,
            "files_analyzed": 0,
            "hotspots": 0,
            "knowledge_silos": 0,
            "coupling_links": 0,
            "overall_bus_factor": 0,
            "total_additions": 0,
            "total_deletions": 0,
        },
        "insights": [
            {
                "severity": "low",
                "title": "No history found",
                "detail": "Create a few commits or adjust the since/exclude filters, then scan again.",
            }
        ],
        "files": [],
        "coupling": [],
        "contributors": [],
        "timeline": [],
    }
