# Contributing to RepoRadar

Thanks for your interest in contributing! RepoRadar is a Python CLI tool — contributions of all sizes are welcome, from bug fixes to new signals.

---

## Dev Environment Setup

**Requirements:** Python 3.9+, pip, git

```bash
# 1. Fork and clone
git clone https://github.com/SemTiOne/reporadar
cd reporadar

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your environment
cp .env.example .env
# Edit .env — add your GITHUB_TOKEN
```

---

## Running Tests

```bash
pytest tests/
```

Run a specific file:
```bash
pytest tests/test_signals.py -v
```

With coverage:
```bash
pip install pytest-cov
pytest tests/ --cov=. --cov-report=term-missing
```

All 174 tests must pass before submitting a PR.

---

## Running the CLI Locally

```bash
python -m cli.main check user/repo
python -m cli.main compare user/repo-a user/repo-b
python -m cli.main doctor
```

---

## Building the Docker Container

```bash
# CLI container
docker build -f deploy/Dockerfile -t reporadar .
docker run --env-file .env reporadar check user/repo

# License server
docker build -f deploy/Dockerfile.server -t reporadar-server .
```

---

## Code Style

- **Type hints** required on all functions
- **Docstrings** required on all public modules, classes, and functions
- Format with [black](https://black.readthedocs.io/): `black .`
- All signals must extend `BaseSignal` and **never raise exceptions**
- All validation goes through `validator.py` — no duplicate validation
- All GitHub API calls go through `core/github_client.py` only
- Never log raw tokens — always use `security.mask_token()`
- Use `rich` for all terminal output — no plain `print()` calls

---

## Adding a New Signal

1. Create `core/signals/your_signal.py` extending `BaseSignal`
2. Add it to `core/signals/__init__.py`
3. Add signal name to `subscription/tiers.py` (`FREE_SIGNALS` or `PAID_SIGNALS`)
4. Add tests in `tests/test_signals.py`
5. Update the signal table in `README.md`

Signals must:
- Never raise exceptions — return a bad score with error detail instead
- Return a `SignalResult` with all fields populated
- Have a clear weight that sums sensibly with existing weights

---

## Pull Request Process

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Write tests for new functionality
3. Ensure all tests pass: `pytest tests/`
4. Add a changelog entry under `[Unreleased]` in `CHANGELOG.md`
5. Open a PR with a clear description of the change and why

---

## Phase 2 Contributions

Phase 2 converts the CLI into a web service. If you want to contribute:

- `api/routes.py` stubs are the target — replace with real `RepoAnalyzer` calls
- Add API key auth via `X-RepoRadar-Key` header
- Wire `/history` to a server-side database
- The Chrome Extension (Phase 3) calls `GET /analyze?repo=owner/repo`

All core logic (`core/`, `cache/`, `history/`, `subscription/`) is Phase 2-ready — no refactoring needed.

---

## Reporting Bugs

Open a [GitHub Issue](https://github.com/SemTiOne/reporadar/issues) with:
- Your OS and Python version
- The command you ran
- The full error output
- Output of `reporadar doctor`

---

## Security Vulnerabilities

**Do not open a public issue for security vulnerabilities.**

Email: **emphyst80@gmail.com** with subject "RepoRadar Security"

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

We'll acknowledge within 48 hours and aim to patch within 7 days. Credit will be given in the changelog.

---

## Questions?

Open a [GitHub Discussion](https://github.com/SemTiOne/reporadar/discussions) or email emphyst80@gmail.com.