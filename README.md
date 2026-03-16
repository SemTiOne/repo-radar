# RepoRadar 🔍

![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-174%20passing-brightgreen)

**Instantly know if a GitHub repository is alive, dying, or dead.**

Before adding a dependency to your project, RepoRadar tells you if it's still actively maintained — with a health score out of 100, a **Dead / Alive / Uncertain** verdict, and a full signal breakdown, all from your terminal.

```
reporadar check discordjs/discord.js
```

```
╭──────────────────────────── RepoRadar Analysis ────────────────────────────╮
│  ✅ discordjs/discord.js                                                    │
│  Score: 89.0/100  (Healthy)                                                 │
│  Verdict: ALIVE                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯
```

---

## Why RepoRadar?

You're about to add a library to your project. But:
- When was the last commit?
- Are issues being responded to?
- Is anyone still maintaining it?

Checking all of this manually takes 10 minutes per repo. RepoRadar does it in seconds.

---

## Quick Start

```bash
# Install
git clone https://github.com/SemTiOne/reporadar
cd reporadar
pip install -r requirements.txt

# Add your GitHub token (recommended — free at github.com/settings/tokens)
cp .env.example .env
# Edit .env and set GITHUB_TOKEN=ghp_...

# Run
python -m cli.main check user/repo
```

---

## All Commands

```bash
# Check a single repo
reporadar check user/repo
reporadar check https://github.com/user/repo
reporadar check user/repo --format json
reporadar check user/repo --format markdown
reporadar check user/repo --badge          # generate README badge
reporadar check user/repo --watch          # re-check every 5 minutes
reporadar check user/repo --watch --interval 60

# Compare two repos side by side
reporadar compare facebook/react vuejs/vue
reporadar compare expressjs/express fastify/fastify

# Bulk check (Pro)
reporadar bulk repos.txt
reporadar bulk --from-package-json ./package.json
reporadar bulk --from-requirements ./requirements.txt

# History (Pro)
reporadar history
reporadar history --repo user/repo
reporadar history --stats
reporadar history --trend user/repo

# Maintenance
reporadar doctor
reporadar cache clear
reporadar cache stats
```

---

## Signals

| Signal | Free | Weight | What It Measures |
|--------|:----:|:------:|-----------------|
| `commit_recency` | ✅ | 25% | Days since last commit |
| `commit_frequency` | 💎 | 20% | Recent vs historical commit rate |
| `issue_response` | 💎 | 15% | Avg maintainer response time |
| `pr_merge_rate` | 💎 | 15% | % of closed PRs that were merged |
| `release_frequency` | 💎 | 10% | Days since last GitHub release |
| `contributor_activity` | 💎 | 10% | Active contributors (last 90 days) |
| `issue_ratio` | ✅ | 3% | % of issues that are open |
| `archive_status` | ✅ | 2% | Whether the repo is archived |

✅ Free &nbsp;&nbsp; 💎 Pro

---

## Scoring

| Score | Label | Verdict |
|:-----:|-------|:-------:|
| 80–100 | Healthy | ✅ Alive |
| 60–79 | Maintained | ✅ Alive |
| 40–59 | Slowing Down | ⚠️ Uncertain |
| 20–39 | Barely Alive | ⚠️ Uncertain |
| 0–19 | Dead | 💀 Dead |

- **Archived repo** → always 💀 Dead (overrides score)
- Score ≥ 60 → ✅ Alive
- Score 35–59 → ⚠️ Uncertain
- Score < 35 → 💀 Dead

---

## Free vs Pro

| Feature | Free | Pro |
|---------|:----:|:---:|
| Single repo check | ✅ | ✅ |
| 3 core signals | ✅ | ✅ |
| All 8 signals | ❌ | ✅ |
| Compare two repos | ❌ | ✅ |
| Watch mode | ❌ | ✅ |
| JSON / Markdown export | ❌ | ✅ |
| Bulk check (up to 50 repos) | ❌ | ✅ |
| History & trend analysis | ❌ | ✅ |
| README badge generation | ❌ | ✅ |
| No watermark | ❌ | ✅ |

### 💎 Get Pro — $29 one-time, lifetime license

No subscription. Pay once, use forever.

**[Buy RepoRadar Pro — $29 →](https://www.paypal.com/ncp/payment/5X6DW442HHETW)**

After payment, email **emphyst80@gmail.com** with your PayPal transaction ID and you'll receive your license key within 24 hours.

Activate it in your `.env`:
```env
LICENSE_KEY=RRADAR-XXXXXXXXXXXXXXXX-XXXXXXXX
```

---

## README Badge

Add a health badge to your own repo after checking it:

```bash
reporadar check user/repo --badge
```

Output:
```markdown
[![RepoRadar](https://img.shields.io/badge/RepoRadar-87%2F100%20Healthy-brightgreen)](https://github.com/user/repo)
```

---

## GitHub Token Setup

Without a token: 60 API requests/hour. With a token: 5,000/hour.

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate new token (classic) — check `public_repo` scope
3. Add to `.env`:
```env
GITHUB_TOKEN=ghp_your_token_here
```

---

## System Health Check

```bash
reporadar doctor
```

Runs 16 checks: API connectivity, token validity, cache, history permissions, disk space, memory, Python version, and more.

---

## Roadmap

```
Phase 1 ✅  CLI tool (current)
Phase 2 🔜  Website — analyze any repo from your browser
Phase 3 🔜  Chrome Extension — see health score on GitHub pages
```

---

## Deployment

| Option | Cost | Notes |
|--------|:----:|-------|
| Railway | ~$0.50/mo | `railway up` — config included |
| Fly.io | Free tier | `fly launch` — config included |
| Self-host | Your cost | Docker config included |

---

## Security

- GitHub tokens never logged — always masked
- History file `chmod 600` on every write (Unix/macOS)
- License keys cryptographically signed (HMAC-SHA256)
- No telemetry, no data collection

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built by [SemTiOne](https://github.com/SemTiOne)*