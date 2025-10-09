# 📜 Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.2.1] - 2025-10-09

### Fixed

- Typo in `edgar.py` (`parents=True` instead of `Trust`).
- Syntax error in `summarize.py` import (`from re` → `import re`).

### Improved

- TF-IDF summarizer now retries without stopwords when vocabulary is empty.
- All pytest suites now pass locally (analyst + core modules).

---

## [v0.2.0] - 2025-10-08

### Added

- Analyst module: fetch and cache SEC filings.
- HTML extraction for MD&A and Risk Factors.
- TF-IDF-based summarizer for insights.
- Unit tests for parsing and summarization.

---

## [v0.1.0] - 2025-10-05

### Added

- Initial FinOps platform structure.
- Shared `report_template.py` with auto-publishing to GitHub Pages.
- Manual workflows for Analyst and Trader modules.
