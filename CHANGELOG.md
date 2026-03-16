# Changelog

All notable changes to RepoRadar are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.0] - 2026-03-16

### Added
- `--watch` flag — continuously re-check a repo at a fixed interval with a live dashboard
- `--interval` flag — set seconds between re-checks in watch mode (default: 300s)
- `--badge` flag — generate shields.io badge snippets in Markdown, HTML, and RST
- `compare` subcommand — side-by-side signal comparison of two repositories with winner indicators
- Cryptographic license key system — HMAC-SHA256 signed keys, unforgeable without server secret
- License validation server (`licensing/key_server.py`) — deployable to Railway free tier
- Online license validation with 3-day offline grace period and local cache
- Key revocation endpoint — instantly invalidate keys for refunds or chargebacks
- Per-IP rate limiting on validation server (10 req/min)
- `scripts/generate_key.py` — generate and email license keys after PayPal payment
- `.env` file permission check in `reporadar doctor`
- `deploy/Dockerfile.server` — separate Docker image for license server
- `deploy/railway.server.json` — Railway config for license server
- `DEPLOY_SERVER.md` — step-by-step Railway deployment guide

### Changed
- License validation upgraded from regex-only to 3-layer defence (format + HMAC + online)
- `subscription/license.py` fully rewritten with offline grace period and local cache
- `RRADAR-XXXXXXXXXXXXXXXX-XXXXXXXX` key format (16-char payload + 8-char HMAC signature)

### Security
- License keys now cryptographically signed — forged keys rejected without server contact
- Constant-time HMAC comparison (`hmac.compare_digest`) prevents timing attacks
- No customer PII stored in license keys — payload is a one-way hash
- `keys_issued.log` added to `.gitignore` — never committed to version control

---

## [0.1.0] - 2026-03-14

### Added
- Initial release of RepoRadar CLI
- 8 health signals with weighted scoring:
  - `commit_recency` (free, 25%) — days since last commit
  - `commit_frequency` (pro, 20%) — recent vs historical commit rate
  - `issue_response` (pro, 15%) — average maintainer response time
  - `pr_merge_rate` (pro, 15%) — percentage of PRs merged
  - `release_frequency` (pro, 10%) — days since last release
  - `contributor_activity` (pro, 10%) — active contributors in last 90 days
  - `issue_ratio` (free, 3%) — percentage of issues that are open
  - `archive_status` (free, 2%) — whether the repo is archived
- Health score 0–100 with label: Healthy / Maintained / Slowing Down / Barely Alive / Dead
- Dead / Alive / Uncertain verdict with emoji indicators
- Free tier (3 signals) and Pro tier (all 8 signals)
- Local file cache with configurable TTL
- Local history and audit logging with trend analysis
- Bulk checking from `.txt`, `package.json`, `requirements.txt`
- JSON and Markdown export
- GitHub API rate limit awareness and warnings
- `reporadar doctor` — 16-point system health check
- Phase 2 FastAPI routes stubbed for website and Chrome Extension
- Docker, Railway, and Fly.io deployment configurations
- Full test suite — 174 tests across 10 test files