# GitFossil — Project Story

A local-first engineering intelligence tool that turns Git history into an explainable, interactive repository risk map.

Live demo: https://Seeeeean0222.github.io/gitfossil/

## One-line pitch

Built a zero-dependency Python CLI that reconstructs engineering risk from Git history, combining hotspot scoring, knowledge concentration, bus-factor analysis and cross-directory co-change detection in a portable offline HTML report.

## Engineering highlights

- Designed an explainable 0–100 file-risk model with five normalized signals and visible evidence.
- Implemented file-level knowledge silos, project bus factor, ownership handoffs and temporal activity aggregation.
- Detected hidden dependencies using confidence, support and lift; suppressed noise from low-support pairs and bulk-refactor commits.
- Parsed Git history in one subprocess, normalized rename destinations and supported commit limits, date ranges, branch selection and path exclusions.
- Built a self-contained interactive dashboard with search, risk details, coupling views, timeline visualization and print styling.
- Covered parsing and analysis with 14 automated tests against temporary real Git repositories; validated on Python 3.9, 3.12 and 3.13 in CI.
- Published a deterministic GitHub Pages demo and regenerated it in CI to catch report drift.

## Resume bullets — 中文

- 独立设计并实现 GitFossil：一个零第三方运行时依赖的 Git 仓库风险分析 CLI，将提交历史转化为可交互、可离线分享的工程健康报告。
- 构建包含变更频率、代码搅动、所有权集中度、知识单点风险和时效性的可解释文件风险模型，并实现知识孤岛、项目 Bus Factor、所有权交接等指标。
- 基于 confidence、support 与 lift 建立文件共变分析，识别跨目录隐性耦合；通过提交规模和置信度阈值降低批量重构产生的误报。
- 使用 Python 标准库完成 Git 历史单次采集、重命名归一、过滤和 HTML 内嵌渲染；14 个自动化测试覆盖真实临时 Git 仓库，并通过 Python 3.9/3.12/3.13 CI。
- 设计本地优先架构与单文件离线报告，避免源码上传和前端依赖，同时使用 GitHub Actions 完成 CI 与 Pages 自动部署。

## Resume bullets — English

- Built GitFossil, a zero-runtime-dependency Python CLI that converts Git history into an explainable, portable engineering-risk dashboard.
- Designed a weighted file-risk model spanning change frequency, churn, ownership concentration, bus factor and staleness, with visible evidence for every score.
- Implemented confidence/support/lift-based co-change analysis to surface cross-directory hidden dependencies while filtering low-support pairs and bulk refactors.
- Added single-pass Git collection, rename normalization, path exclusions and deterministic offline HTML rendering; validated 14 integration/unit tests across Python 3.9, 3.12 and 3.13.
- Shipped a local-first architecture, self-contained reports, GitHub Actions CI and an automatically deployed interactive demo.

## Interview talking points

1. **Why the model is explainable:** every file exposes the signals and weighted inputs behind its score, avoiding an opaque “AI risk” claim.
2. **How false positives are reduced:** coupling requires repeated support and confidence; commits touching more than 40 files are ignored as broad refactors.
3. **Trade-offs:** email is a stable author key but can merge shared machines; co-change is a hypothesis, not proof of a dependency.
4. **Why no web framework:** the product output is a static report, so a dependency-free pipeline keeps installation and security review simple.
5. **What can be measured next:** compare findings with legitimate user study feedback, false-positive review time and behavior on large open-source repositories. Do not invent adoption or impact metrics.

## Verifiable evidence

- Source and tests: https://github.com/Seeeeean0222/gitfossil
- Interactive demo: https://Seeeeean0222.github.io/gitfossil/
- Methodology: [METHODOLOGY.md](METHODOLOGY.md)
- Test suite: `python -m unittest discover -s tests -t . -v`
