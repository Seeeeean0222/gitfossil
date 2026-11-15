# Methodology

GitFossil is deliberately explainable. It samples commit history with `git log
--numstat`, applies optional path filters, and computes a small set of
interpretable signals. It does not read source code semantics and it is not an
AI classifier.

## File risk

The 0–100 risk score combines five normalized signals:

| Signal | Weight | Interpretation |
| --- | ---: | --- |
| Change frequency | 32% | Logarithmic count of commits touching the file |
| Churn | 23% | Logarithmic additions plus deletions |
| Ownership concentration | 23% | Excess change share above 50% held by the top author |
| Ownership fragility | 12% | Penalty when the file's 80% bus factor is low |
| Recency | 10% | Time since last touch relative to sampled history |

This is a triage score, not an absolute code-quality measure. A small,
frequently edited configuration file can score highly because it is operationally
important.

## Knowledge silos

A file is labelled a potential knowledge silo when it has at least three sampled
changes and one email identity accounts for at least 75% of them. The project bus
factor is the minimum number of contributors whose commits add up to 80% of all
sampled commits.

The report normalizes author identity by email rather than display name. This is
more stable but may merge people who share an address or split one person who
uses several addresses.

## Hidden coupling

Two files form a coupling link when they change in at least two commits, achieve
at least 35% confidence, and represent at least 1.5% of eligible commits. Commits
touching more than 40 files are ignored because broad refactors create many
spurious pairs.

For files A and B:

```text
confidence = cochanges(A, B) / min(changes(A), changes(B))
support    = cochanges(A, B) / eligible_commits
lift       = cochanges(A, B) * eligible_commits / (changes(A) * changes(B))
```

A cross-directory pair is called a "hidden dependency" hypothesis. It deserves
investigation; it does not prove that a dependency is missing.

## Known limitations

- Merge commits are excluded by default.
- File-level history cannot see function ownership or semantic changes.
- Generated files can dominate results unless excluded with `--exclude`.
- Rename detection is heuristic and follows the destination path.
- Commit identity is a proxy for ownership, not actual team responsibility.
