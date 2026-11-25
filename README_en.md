# New Tea Quant (NTQ) — Quantitative Research Framework for A-Shares

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.6.0-8A2BE2"></a>&nbsp;
  <a href="#"><img alt="Platform" src="https://img.shields.io/badge/platform-mac%20%7C%20linux%20%7C%20win-4CAF50"></a>&nbsp;
  <a href="#"><img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white"></a>&nbsp;
  <a href="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml"><img alt="Build" src="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml/badge.svg"></a>&nbsp;
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-NTQ%20%7C%20commercial%20by%20authorization-007EC6"></a>
</p>

> For the Chinese introduction, see **[here](README.md)**.

Author: Garnet Xin & his AI companions

<a href="https://github.com/garnet1985/new-tea-quant"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-new--tea--quant-181717?logo=github&logoColor=white"></a>&nbsp;
<a href="https://gitee.com/garnet/new-tea-quant"><img alt="Gitee" src="https://img.shields.io/badge/Gitee-new--tea--quant-C71D23?logo=gitee&logoColor=white"></a>&nbsp;
<a href="https://new-tea.cn"><img alt="Website" src="https://img.shields.io/badge/website-new--tea.cn-009688?logo=google-chrome&logoColor=white"></a>

Install now? → [One-command install](#one-command-install) · [Setup guide](https://new-tea.cn/zh-hans/setup) · [Quick intro (screenshots)](https://new-tea.cn/zh-hans/quick-intro) · [Tutorials](https://new-tea.cn/zh-hans/more-examples) · [Register](https://new-tea.cn/zh-hans/user/register)

---

## Current version (v0.6.0)

**License update**: Through 0.5.3, NTQ used Apache-2.0 and could be used freely. From 0.6.0 onward it uses the NTQ terms: non-commercial use still follows Apache-2.0 principles; commercial use needs the author’s authorization. See [LICENSE](LICENSE) and the site [terms](https://new-tea.cn/zh-hans/disclaimer).

**NTQ AI agent is live**: [Register as a member](https://new-tea.cn/zh-hans/user/register) and you get a monthly free AI quota (“cat food” / 猫粮). The New Tea assistant can help with in-app work, including writing code. How to load a membership credential: [Import membership credential](#import-membership-credential).

Summary: **[CHANGELOG.md](CHANGELOG.md)**. This release includes breaking changes (strategy hooks, indicator naming, DB tables, post-process config format, Python ≥ 3.11, NTQ license, and more).

**From 0.6.x onward**, NTQ will not keep adding large new feature blocks. Updates will focus more on:

- Locking APIs (so locking avoids breaking changes)
- AI agent development
- Code cleanup and optimization
- Documentation

---

## What is New Tea Quant?

New Tea Quant (NTQ) is an AI-assisted, personal-developer-friendly, declarative, plugin-oriented framework for quantitative strategy backtesting and research. (**New Tea** is named after the author’s British Shorthair “新茶”; she is also the name of the in-app AI assistant.)

NTQ does two things:

- Put your quantified stock-picking and trading rules into historical data to see whether they work (validate the “quant” rules)
- Scan the latest market with those rules, find opportunities, and report them (use the “quant” rules to hunt)

### Where is the boundary?

The open-source free edition only covers strategy validation, debugging, and related capabilities:

- **Does not include** external data feeds (ships with demo data for ~300 sample names, 2023-01-01 – 2025-12-31)
- **Does not include** a bundled LLM ([register](https://new-tea.cn/zh-hans/user/register) to use NTQ’s hosted AI with a monthly free quota)
- **Does not include** post-scan execution modules (e.g. auto-order, SMS; members get a limited email notification quota)

After you [register](https://new-tea.cn/zh-hans/user/register), you move from “open-source framework” into the “product boundary” and additionally get:

- More demo data (300 → ~5800+ names across the market, same date range; import under **Settings → Install & maintenance**)
- A monthly free AI quota (cat food)
- A one-time email quota for post-scan notifications

All demo data is for demonstration only — do not use commercially. AI replies are suggestions only; NTQ is not responsible for any outcome.

---

## One-command install

From the **project root**:

```bash
python3 launcher.py
```

Follow the UI prompts (defaults are fine). Step-by-step screenshots: [Install New Tea Quant](https://new-tea.cn/zh-hans/setup).

**Notes**

- Install and launch use the same command; if already installed, it skips setup and starts the app.
- Local Python may be `python` or `python3`; the launcher path may be `launcher.py` or `./launcher.py`. Try combinations if the first fails.
- 0.5.x minimum Python was 3.9; from 0.6.0 it is **3.11**. Prefer 3.11–3.12: newer Pythons may lack wheels for some dependencies. Check with `python3 --version`.

---

## Import membership credential

To unlock more NTQ services, including:

- More demo data (~300 names → ~5800+ names, 3 years)
- New Tea AI assistant (monthly free quota)
- A one-time email demo quota for post-scan processing

[Register](https://new-tea.cn/zh-hans/user/register) on the site, then link your local app with a **universal credential**. Screenshots: [Setup · Import membership credential](https://new-tea.cn/zh-hans/setup).

1. After [registration](https://new-tea.cn/zh-hans/user/register), click your avatar at the top-right of the homepage to open your profile:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2012.01.06.png" alt="Open profile" width="800" />
</p>

2. Below your profile info you will see cat food (AI quota) and the **universal credential** (the site may mask it; yours should be a random string). Copy it:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2012.02.22.png" alt="Copy universal credential" width="800" />
</p>

3. In the NTQ app, go to **Settings → Membership**, paste the credential and load it. A green badge appears on success:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2012.04.39.png" alt="Paste credential in Settings" width="800" />
</p>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2012.11.36.png" alt="Credential loaded" width="800" />
</p>

**Important**: Treat the universal credential like a product password. If it leaks, refresh it on the website immediately and re-import.

---

## What can NTQ do?

Everything below can be driven by the New Tea AI assistant, or by a local agent (Workbuddy, Harness, TreaWorker, Doubao, etc.). Fuller screenshots: [Quick intro](https://new-tea.cn/zh-hans/quick-intro).

**Note**

- Default DB is DuckDB, which allows only one writer at a time. If the UI and a third-party agent both run NTQ, they may fight over the DB — keep only one process open. MySQL / PostgreSQL do not have this limit.

### Strategy design & backtest

Usually **two ways** to build a strategy:

- Follow the userspace examples: opportunity logic in `strategy.py`, parameters in `settings.py`.
- Talk to the New Tea AI assistant and let it write code and report results.

And **two ways** to tune:

- Edit `settings.py`. Any config change creates a new strategy version; compare and switch freely.
- Ask the AI assistant to change parameters via chat.

Backtest has **four steps**, each runnable alone with its own report; AI can help with any step:

- **Opportunity enumeration**: Find all hits in history; check density and concentration — does the strategy find opportunities well?
- **Price backtest**: Filter duplicates, then see whether those hits meet your investment goals — is the strategy basically profitable?
- **Portfolio simulation**: Virtual capital + your money rules — can you capture the edge from the previous step? Closest automated stand-in for live trading.
- **Decision simulation**: Same as above, but **you** choose what and how much to buy. The critical check that the strategy fits *you*, including stress many backtesters ignore.

Also:

- **Parameter attribution**: How parameters move results and sensitivity (needs the ML plugin).
- **Rolling contrast**: Roll the same strategy across different windows and compare.

#### Strategy UI

Strategy page: header = strategy info, left = parameters, right = run panel and reports.

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.01.25.png" alt="Strategy page" width="800" />
</p>

Price-backtest report:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.50.30.png" alt="Price backtest report" width="800" />
</p>

Open a single name to see entries and exits clearly:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.51.15.png" alt="Single-name entry/exit" width="800" />
</p>

Compare results across strategy versions:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.52.03.png" alt="Version compare" width="800" />
</p>

Or see which parameter changes drove the difference:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.53.13.png" alt="Parameter diff" width="800" />
</p>

Price-layer attribution — how results change when parameters take different values:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.55.02.png" alt="Attribution report" width="800" />
</p>

Rolling contrast across windows:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.56.08.png" alt="Rolling contrast" width="800" />
</p>

Decision-maker mode — time advances; you make the investment calls:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2011.18.20.png" alt="Decision-maker mode" width="800" />
</p>

As time moves on, you see P&L from your decisions — a historical live-trading rehearsal with your own strategy:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2011.19.57.png" alt="Decision-maker P&L" width="800" />
</p>

Or let the New Tea AI assistant run the backtest:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.57.02.png" alt="AI assistant chat" width="480" />
</p>

AI assistant reporting backtest results:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.58.07.png" alt="AI assistant results" width="480" />
</p>

### Strategy scanning (stock picking)

Use a tuned strategy to scan which names currently match; then wire [post-processing](#post-scan-opportunity-handling) for auto-trading, filters, alerts, ML, etc. Without post-processing, results still show in the UI.

**Notes**

- Only demo data ships; live data needs your own feed.
- Post-processing is yours to configure; members get a limited demo email quota.

Scan UI: demo mode uses the configured latest trading day (simulated); strict mode probes the real latest day and refuses if data is short.

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.09.37.png" alt="Strategy scan UI" width="800" />
</p>

Scan report — then post-process for filter / notify / trade / analyze:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.12.59.png" alt="Scan report" width="800" />
</p>

### Feature tags

Think “factors”: abstract features in code and bind them to entities. E.g. market cap > 5B = “large”, else “small”, precompute for all names, reuse across strategies without recalculating. Building tags is building your factor library.

Tag list and outputs:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.14.58.png" alt="Feature tag list" width="800" />
</p>

Outputs can be visualized by type:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.15.21.png" alt="Feature tag chart" width="800" />
</p>

### External data sources

Framework for plugging in external feeds: multithreading, your rate limits to avoid bans, config-driven setup, retries, resume, etc.

Data-source UI — which feeds, how they update, whether data is fresh:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.17.12.png" alt="Data source UI" width="800" />
</p>

### Data contracts

A core piece of “config-driven” NTQ: contracts standardize structure and reads so you **declare** what you need and get injection automatically.

Contract list — injectable data, keys, types:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.19.03.png" alt="Data contracts" width="800" />
</p>

### Series relation

Correlation and lag across series: inverse moves, lead–lag, or how a macro event affects market liquidity.

UI example — two banks vs one liquor close price:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.20.56.png" alt="Series relation UI" width="800" />
</p>

Result: the two banks move together (~0.73); liquor vs banks is inverse (negative correlation):

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.22.19.png" alt="Series relation result" width="800" />
</p>

### Post-scan opportunity handling

Also called scan post-processing: what to do after a scan. Create plans; each plan picks executable units (adapters); after the scan, NTQ runs them in dependency order.

**Notes**

- Only **two** units work out of the box: **presenter** (load backtest stats when showing opportunities) and **ntq email service** (site email; one-time member demo quota).
- Other units are demos — implement them yourself or get third-party credentials.

Plan list (steps and availability):

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.24.50.png" alt="Post-process plans" width="800" />
</p>

Small unit list:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.25.13.png" alt="Post-process units" width="800" />
</p>

Build a plan, drop in units; NTQ sorts and runs by dependency:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.25.35.png" alt="Edit post-process plan" width="800" />
</p>

### Settings

Preferences and system config (membership credential, demo data cutoff, cache cleanup, etc.). [Register](https://new-tea.cn/zh-hans/user/register) for AI / email quotas; load steps: [Import membership credential](#import-membership-credential).

### Command line

Most features run from the CLI — different entry points by role:

```bash
python cli.py     # end users: day-to-day commands (help below)
python devcli.py  # developers: shortcuts (help below)
```

User `cli.py` help:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2011.25.38.png" alt="cli.py help" width="800" />
</p>

Developer `devcli.py` help:

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2011.25.22.png" alt="devcli.py help" width="800" />
</p>

Use without the UI, or build on top.

---

## Star NTQ

[GitHub](https://github.com/garnet1985/new-tea-quant) · [Gitee](https://gitee.com/garnet/new-tea-quant) · Feedback: [contact](https://new-tea.cn/zh-hans/contact)

## License & support

See [LICENSE](LICENSE) and site [terms](https://new-tea.cn/zh-hans/disclaimer). Non-commercial vs commercial terms follow the license and [CHANGELOG](CHANGELOG.md).

---
