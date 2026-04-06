# Changelog

All notable changes to `kanboard-cli` are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.3] — 2026-04-06

### Added
- **Security fuzzing framework** — two-layer security testing suite
  - JSON-RPC API fuzzing against live Docker Kanboard: SQL injection, XSS, path traversal, command injection, type confusion, boundary values, null bytes, unicode edge cases, protocol abuse, and authentication boundary testing
  - Plugin method fuzzing from `api-schema.json` (SQLi + type confusion across all 31 plugin methods)
  - Python-native property-based fuzz testing via Hypothesis: SDK client serialization, model deserialization, config resolution, CLI input handling, and response parsing
  - Bandit static security analysis and pip-audit dependency vulnerability scanning
- `scripts/security-fuzz.sh` — orchestration script with `--no-docker` and `--api-only` flags
- `.github/workflows/security-fuzz.yml` — nightly (04:00 UTC), post-release, and manual-dispatch workflow
- `[security]` optional dependency group: `bandit`, `pip-audit`, `hypothesis`
- `security` pytest marker (excluded from default test runs)

### Changed
- `.gitignore` — added `reports/`, `.hypothesis/`, and auto-generated SDK/CLI module directories

## [Unreleased]

### Added
- Project scaffolding: `src/` layout, `pyproject.toml`, Makefile, LICENSE (US-001)
