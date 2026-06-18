# New Tea Quant (NTQ) — A-Share Quantitative Research Framework

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.4.1-8A2BE2"></a>&nbsp;
  <a href="#"><img alt="Platform" src="https://img.shields.io/badge/platform-mac%20%7C%20linux%20%7C%20win-4CAF50"></a>&nbsp;
  <a href="#"><img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white"></a>&nbsp;
  <a href="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml"><img alt="Build" src="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml/badge.svg"></a>&nbsp;
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-007EC6"></a>
</p>

> For the **canonical, fully maintained documentation** (Chinese), see **[README.md](README.md)**.

Author: Garnet Xin & his AI assistant

<a href="https://github.com/garnet1985/new-tea-quant"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-new--tea--quant-181717?logo=github&logoColor=white"></a>&nbsp;
<a href="https://gitee.com/garnet/new-tea-quant"><img alt="Gitee" src="https://img.shields.io/badge/Gitee-new--tea--quant-C71D23?logo=gitee&logoColor=white"></a>&nbsp;
<a href="https://new-tea.cn"><img alt="Website" src="https://img.shields.io/badge/website-new--tea.cn-009688?logo=google-chrome&logoColor=white"></a>

## Current release (v0.4.x)

Since **v0.4.0**, NTQ uses **embedded DuckDB** file storage. You no longer need a third-party database server to run — **Python alone is enough**. MySQL and PostgreSQL remain supported if you prefer them.

Recent highlights:

**v0.4.1**

- Added **3 demo groups (9 strategies in total)** to help you learn the framework step by step. **Note: these demos are for illustration only — not investment advice.**
- In enumeration and price-layer reports you can now **click a single stock** to view its K-line chart and buy/sell markers, making strategy debugging more intuitive.
- See [CHANGELOG.md](CHANGELOG.md) for the full list.

## What is NTQ?

Do you have ideas about stock tactics you want to test — e.g. whether weekly RSI below 20 is worth buying, whether MACD golden crosses have an edge, or how “hot theme” chasing actually performs? **NTQ (New Tea Quant)** is a **local, end-to-end A-share research framework** that helps you turn “I have an idea” into “I have evidence,” not a one-off black-box backtest.

### Core value: layered backtesting

NTQ splits research into three steps, each answering a different question:

1. **Opportunity enumeration** — *when* and *on which stocks* does your logic trigger in the sample?
2. **Price-layer validation** — after a trigger, how does a **single round-trip** behave under fees, slippage, and your execution assumptions?
3. **Capital-layer simulation** — with **limited cash, position rules, and market constraints**, does the idea still hold at the portfolio level?

Separating signal quality, trade-level P&amp;L, and capital constraints makes it easier to see whether the problem is the **signal**, the **rules**, or **position sizing**. Enumeration output is stored as structured artifacts you can reuse, compare, and analyze.

### What else you get

- **All-in-one locally**: data ingest &amp; storage, indicators/tags, backtests, and full-market scanning in one repo; **`core`** vs **`userspace`** separation so your strategies and config survive framework upgrades.
- **Config-driven workflow**: most experiments are configuration changes; reach for Python when logic gets complex. The **Strategy Lab Web UI** (backtests, reports, version compare) and the CLI run the **same** strategy definitions.
- **Reproducibility**: version snapshots, fingerprints, and structured result directories so you can answer “what changed since last run?”
- **Performance**: multi-process / multi-threaded core paths so a typical desktop can handle large samples.

After research, use **strategy scan** to filter the latest universe; opportunities are shown in the terminal or Web UI by default — notifications and live trading are **your** integrations.

## Support the project

If NTQ helps you and you want to follow its evolution, a **Star** on [GitHub](https://github.com/garnet1985/new-tea-quant) or [Gitee](https://gitee.com/garnet/new-tea-quant) is meaningful support for a solo open-source effort.

This is my first serious open-source project — your feedback keeps me improving the framework. Thank you!

### Please note

NTQ is free and open source, but some capabilities need **your own** resources:

- **Data**: the framework provides connectors and storage — **not** paid data subscriptions or tokens. Register and configure third-party sources yourself.
- **Notifications &amp; trading**: SMS, email, push, and order routing are **outside** the framework. Scan results can be forwarded via Adapter hooks to your own code.

### Also

You need **basic Python / configuration skills** (or AI assistance). Runtime: **Python 3.9+**. Default storage is embedded **DuckDB**; **MySQL / PostgreSQL** are optional in the wizard. Richer tutorials (Chinese) live on **[new-tea.cn](https://new-tea.cn)**.

Licensed under **Apache 2.0** — free to learn, modify, and extend.

## Quick start (~5 minutes)

**Goal:** bring up the stack and run the built-in **`example`** strategy.

### Prerequisites

- **Python 3.9+**. Install guide: [install-python](https://new-tea.cn/zh-hans/install-python) (Chinese page).

### Step 1: Get the code

Either:

- **Git clone** (recommended):

```bash
git clone https://github.com/garnet1985/new-tea-quant.git
cd new-tea-quant
```

- **Download ZIP**: on GitHub use **Code → Download ZIP**, extract, and `cd` into **`new-tea-quant`** (same folder as `launcher.py`).

### Step 2: Start the setup wizard from the repo root

From the **repository root**, run:

```bash
python launcher.py
```

If `python` is too old, try:

```bash
python3 launcher.py
```

The script switches to the repo root, ensures the venv, starts **BFF + frontend**, and opens the browser to the **Setup** wizard (BFF setup API).

### Step 3: Finish initialization in the browser

Follow the on-page steps (database, userspace path, data import — exact flow depends on your build). Reference screenshots (UI labels may be Chinese):

**Figure 1**

![Setup wizard 1](setup/images/step1.png)

Dependencies install automatically — click **「开始安装」** and wait.

**Figure 2**

![Setup wizard 2](setup/images/step2.png)

Configure the **userspace** root:

- Use the **default path** and click **Next**, or
- Check **custom userspace path** and pick a directory with enough disk space (the wizard will warn if the target is non-empty).

**Figure 3**

![Setup wizard 3](setup/images/step3.png)

**Database**: default is **DuckDB** (no extra server). For **MySQL / PostgreSQL**, prepare the server first, enter connection details, then continue. You can change this later under **Settings**.

**Figure 4**

![Setup wizard 4](setup/images/steps.png)

After the DB is ready, **data import** and remaining steps run — this can take a while; keep the page open.

**Figure 5**

![Setup wizard 5](setup/images/step4.png)

When done, click **「前往策略实验室」** (Go to Strategy Lab).

### Run your first strategy (Web or CLI)

**Web (recommended):**

```bash
python launcher.py
```

Open Strategy Lab, pick **`example`**, run enum / price / capital steps and read the reports.

**CLI (price layer example):**

```bash
python start-cli.py sp --strategy example
```

A summary in the terminal means the CLI path works. Full pipeline: `se` (enum), `so` (portfolio) — see the CLI table below.

> **Note:** Root **`python install.py`** is for **first-time CLI install** (deps, userspace, schema, bundled small data). After the wizard you usually **don’t** need it again. For a **larger demo ZIP** from the site, put **one** zip under `setup/init_data/` and run:
>
> ```bash
> python setup/steps/import_data/install.py
> ```
>
> Add `--force` for a full re-import. The bundled small dataset from the wizard is enough for the quick start above.

### More common commands

Help:

```bash
python start-cli.py -h
```

Opportunity enumeration (step 1):

```bash
python start-cli.py strategy_enumerate --strategy example
# or short
python start-cli.py se --strategy example
```

Capital simulation:

```bash
python start-cli.py strategy_portfolio --strategy example
# or short
python start-cli.py so --strategy example
```

Full-market scan:

```bash
python start-cli.py scan --strategy example
# or short
python start-cli.py c --strategy example
```

Feature / label jobs:

```bash
python start-cli.py tag
# or short
python start-cli.py t
```

Customize algorithms and goals under `userspace/strategies/` (settings + worker).

Have fun `^_^` — more examples: [more-examples](https://new-tea.cn/zh-hans/more-examples) (Chinese site).

### Data (read this)

1. **Bundled small dataset** — partial tables for a fast demo only.
2. **Larger (~3-year) demo pack** — **(temporarily unavailable; being fixed)** for fuller backtests: register on **[new-tea.cn](https://new-tea.cn)**, download, **clear** `setup/init_data/`, place **one** zip, then `python setup/steps/import_data/install.py` (`--force` if needed).
3. **Your own source** (e.g. Tushare): [userspace/extensions/data_source/README.md](userspace/extensions/data_source/README.md).

### Early feedback welcome

NTQ is in **v0.x** — setup, docs, and the Web UI are still moving. I can’t cover every OS, DB, and workflow alone. If you try the steps above, I’d love to hear **what felt rough, what was unclear, or what could be simpler**.

**How to reach me:** DM on GitHub/Gitee, or the site **[contact form](https://new-tea.cn/zh-hans/contact)** (no registration required).

## Please note

This is still a **pre-1.0 (v0.x)** release — **API stability is not guaranteed** until **v1.0**. See [CHANGELOG.md](CHANGELOG.md).

## Documentation conventions

- Root **`README.md`** (Chinese) is the **canonical** user-facing entry.
- **CLI entry is `start-cli.py`**; if older docs say `start.py`, trust this README and `python start-cli.py -h`.
- **`docs/development/`** is internal — not part of public doc cleanup for now.
- Each release should update at least **`README.md`** and **`CHANGELOG.md`**.

## What’s in the repo?

| Item | Description |
|------|-------------|
| **Framework code** | `core/`, CLI (`start-cli.py`), UI launcher (`launcher.py`) |
| **Web UI** | `core/ui/bff` + `core/ui/fed` (production build committed — no Node for normal use) |
| **Example strategy** | Built-in **`example`** only — reference for config &amp; APIs |
| **Demo market data** | Small bundled set; larger packs from the website |
| **Tooling** | `devtools/` — Docker notes, release scripts, etc. ([docs/README.md](docs/README.md)) |

## Contact

- **Message**: [new-tea.cn/zh-hans/contact](https://new-tea.cn/zh-hans/contact)
- **Issues**: [GitHub Issues](https://github.com/garnet1985/new-tea-quant/issues) · [Gitee Issues](https://gitee.com/garnet/new-tea-quant/issues)
- Expectations: [SUPPORT.md](SUPPORT.md)

## Branch policy

- **master** — latest release; no direct commits/PRs
- **dev** — integration branch; RC branches cut from master for releases, then merged back to dev
- **bugfix/***, **feature/***, **hotfix/*** — required naming; hotfix branches from RC only

**Docker**: see [devtools/docker/README.md](devtools/docker/README.md) (`Dockerfile`, `docker-compose.yml`, optional PostgreSQL).

## Upgrading

1. Pull or download latest **master**; **keep** your local `userspace/` (strategies, backups, config); overwrite the rest from the release.
2. Run `python install.py` (or let `python start-cli.py` trigger install) to refresh deps; re-import data if the release notes say so (`setup/steps/import_data/install.py`).
3. Web UI: `python launcher.py` — usually no local `npm run build` unless you hack the frontend.

---

## Command line (`start-cli.py`)

Entry: **`start-cli.py`** — with no arguments, shows **`version`** (same as `-v`, `--version`, or `v`).

Pattern: `xx` = command, `-xx` = flag, `--xx` = target param.

| Purpose | Example |
|---------|---------|
| Help | `python start-cli.py -h` |
| Version (default) | `python start-cli.py` or `-v` / `--version` / `v` |
| Renew data | `renew [SOURCE] [-f]` or `r` |
| Scan | `scan` or `c [--strategy example]` |
| Enumerate | `strategy_enumerate` or `se [-f] [--strategy example]` |
| Price-factor sim | `strategy_price_factor` or `sp [-f] [--strategy example]` |
| Portfolio sim | `strategy_portfolio` or `so` |
| Capital allocate (use `so` instead) | `strategy_capital_allocate` or `sa` |
| Full sim chain | `strategy_simulate` or `s` |
| Analyze summaries | `strategy_analyse` or `sy` |
| Tag / feature jobs | `tag` or `t` |
| Check core updates | `update` or `u` |

**`--strategy`**: if omitted and exactly one strategy has `is_enabled=True`, it is picked automatically; with several enabled, the first by name is used with a **warning** — prefer an explicit `--strategy`.

Older docs mentioning `start.py` or root **`cli.py`** as the app entry are obsolete — use **`start-cli.py`**.

---

## Developer commands (`devcli.py`)

Local dev / troubleshooting (repo root):

```bash
python devcli.py -h
```

| Purpose | Example |
|---------|---------|
| Start UI (free ports, `launcher.py -d`) | `python devcli.py -ui` |
| Kill listeners on 8000 / 8888 | `python devcli.py -kui` |
| Clear simulation **disk + DB** cache | `python devcli.py -csc` (same as `-cu`) |
| Clear **DB** workbench snapshots only | `python devcli.py -cdc` |
| Delete strategy **`results/`** dirs only | `python devcli.py -cmc` |
| DuckDB WAL checkpoint | `python devcli.py -dbc` |

Workbench cache HTTP APIs: [db-cache-service.md](core/modules/strategy/docs/db-cache-service.md) §8 (V2-11 / V2-12).

---

## Running tests

```bash
python -m pytest
```

Please ensure tests pass before opening a PR.

## Python dependencies

Lockfiles are managed with **pip-tools**:

- Inputs: `requirements.in`, `requirements-dev.in`
- Locks: `requirements.txt`, `requirements-dev.txt`

Recompile (repo root):

```bash
python3 -m piptools compile --output-file requirements.txt requirements.in
python3 -m piptools compile --output-file requirements-dev.txt requirements-dev.in
```

## Support, feedback &amp; sponsorship

- **Site (demo data, extras)**: [new-tea.cn](https://new-tea.cn)
- **Issues / PR expectations**: [SUPPORT.md](SUPPORT.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Security**: [SECURITY.md](SECURITY.md)

For **donations or commercial inquiries**, use the contacts published on the official site.

---

## License &amp; disclaimer

**Apache License 2.0** — see [LICENSE](LICENSE).

**Disclaimer**: for learning and research only, not investment advice; backtest results do not guarantee future performance.

---

<details>
<summary>In-repo docs &amp; archives</summary>

- Offline index: [docs/README.md](docs/README.md)
- **`devtools/`**: [doc index](docs/README.md) · [Docker](devtools/docker/README.md)

</details>
