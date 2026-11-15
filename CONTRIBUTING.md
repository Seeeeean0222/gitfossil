# Contributing

GitFossil aims to stay dependency-free at runtime and easy to audit. Bug reports,
metric critiques and reproducible repository edge cases are especially welcome.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -t . -v
```

Before opening a pull request:

1. Add a regression test for behavior changes.
2. Run the complete test suite.
3. Generate a report against this repository and check both desktop and narrow layouts.
4. Keep the HTML report offline-first: no CDN, analytics, or network requests.

Metric changes should include the reasoning and limitations in `docs/METHODOLOGY.md`.
Metrics describe repository behavior; they should never be used to rank individuals.
