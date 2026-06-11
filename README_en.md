# New Tea Quant (NTQ) - A-Share Quant Research Framework

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.4.0-8A2BE2"></a>&nbsp;
  <a href="#"><img alt="Platform" src="https://img.shields.io/badge/platform-mac%20%7C%20linux%20%7C%20win-4CAF50"></a>&nbsp;
  <a href="#"><img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white"></a>&nbsp;
  <a href="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml"><img alt="Build" src="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml/badge.svg"></a>&nbsp;
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-007EC6"></a>
</p>

> For the **canonical, fully maintained documentation** (Chinese), see **[README.md](README.md)**.

Author: Garnet Xin & His AI dude

<a href="https://github.com/garnet1985/new-tea-quant"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-new--tea--quant-181717?logo=github&logoColor=white"></a>&nbsp;
<a href="https://gitee.com/garnet/new-tea-quant"><img alt="Gitee" src="https://img.shields.io/badge/Gitee-new--tea--quant-C71D23?logo=gitee&logoColor=white"></a>&nbsp;
<a href="https://new-tea.cn"><img alt="Website" src="https://img.shields.io/badge/website-new--tea.cn-009688?logo=google-chrome&logoColor=white"></a>

## Current release (v0.4.x)

Since **v0.4.0**, NTQ has supported **embedded DuckDB** file storage. As of **v0.4.0**:

- **DuckDB is the default** — you only need **Python 3.9+** to run; **MySQL / PostgreSQL remain optional** in the setup wizard.
- **Engine / pipeline updates** — full layered backtests are roughly **6× faster** than before. See [CHANGELOG.md](CHANGELOG.md).

> **Tip:** This file is a shorter English overview. Screenshots below are from the Chinese UI; labels on your screen may read in Chinese.

### What is NTQ?

**NTQ (New Tea Quant)** is a local quantitative research framework for A-share strategies. It helps you turn ideas into evidence-backed conclusions with **layered backtesting**:

1. **Opportunity enumeration** — when and on which stocks does your logic trigger?
2. **Price-factor validation** — how does a single round-trip perform under fees and slippage?
3. **Capital / portfolio simulation** — does the idea still work with position limits and cash constraints?

You also get a **Strategy Lab Web UI** (backtests, reports, version compare), CLI tools, reproducible snapshots, and optional full-market scanning.

> NTQ is free and open source (Apache 2.0). Market data, notifications, and live trading require your own third-party accounts and integrations.

### Tech stack

- **Language**: Python 3.9+
- **Database**: **DuckDB** (default, file-based under `userspace/system/db/`), or **MySQL / PostgreSQL** if you choose them in setup
- **Web UI**: pre-built assets are in the repo — **Node.js is not required** for normal use (`python launcher.py`)
- **License**: Apache 2.0

---

## Quick start (about 5 minutes)

**Goal:** bring up the stack and run the built-in **`example`** strategy.

### Prerequisites

- **Python 3.9+**. Install guide (Chinese): [install-python](https://new-tea.cn/zh-hans/install-python).
- **No separate database server required** for the default DuckDB path.
- **MySQL or PostgreSQL** only if you opt out of DuckDB in the wizard (Chinese guide: [install-database](https://new-tea.cn/zh-hans/install-database)).

### Step 1: Get the code

Either:

- **Git clone** (recommended):

```bash
git clone https://github.com/garnet1985/new-tea-quant.git
cd new-tea-quant
```

- **Download ZIP**: on the GitHub repo page use **Code → Download ZIP**, extract, and open a terminal in the **`new-tea-quant`** root (the folder that contains `launcher.py`).

### Step 2: Start the setup wizard

From the **repository root**, run one of:

```bash
python launcher.py
```

If `python` is not 3.9+, try:

```bash
python3 launcher.py
```

The script ensures the virtual environment, starts **BFF + frontend**, and opens the browser to the **Setup** wizard.

### Step 3: Complete setup in the browser

Follow the on-page steps. Reference screenshots (UI may be Chinese):

**Figure 1** — dependency install: click **「开始安装」** and wait.

![Setup wizard 1](setup/images/step1.png)

**Figure 2** — **userspace** root: use the default path or a custom directory.

![Setup wizard 2](setup/images/step2.png)

**Figure 3** — **database**: the wizard defaults to **DuckDB** (no extra server). To use **MySQL / PostgreSQL**, configure your server first, then enter connection details in the wizard.

![Setup wizard 3](setup/images/step3.png)

**Figure 4** — data import and remaining steps (may take a while).

![Setup wizard 4](setup/images/steps.png)

**Figure 5** — when finished, open **Strategy Lab**.

![Setup wizard 5](setup/images/step4.png)

### Run the `example` strategy

**Web (recommended):**

```bash
python launcher.py
```

Open Strategy Lab, select **`example`**, and run enum / price / capital steps.

**CLI (price layer example):**

```bash
python cli.py -sp --strategy example
```

Enumeration: `python cli.py -se --strategy example`  
Capital simulation: `python cli.py -sa --strategy example`

> **Note:** Root **`python install.py`** is for **first-time CLI install**. For a **larger demo ZIP** from the site, place a single zip under `setup/init_data/` and run `python setup/steps/import_data/install.py` (add `--force` to re-import).

### More common commands (`cli.py`)

```bash
python cli.py -h
python cli.py -sc --strategy example   # scan (default entry)
python cli.py -t                        # labels / features
```

Use **`--strategy`** when multiple strategies are enabled. Older docs mentioning `start.py` are obsolete — use **`cli.py`**.

Edit files under `userspace/strategies/` to customize settings and workers.

---

## Developer commands (`devcli.py`)

From the repository root (local dev / troubleshooting):

```bash
python devcli.py -h
```

| Purpose | Example |
|---------|---------|
| Start UI (free ports, then `launcher.py -d`) | `python devcli.py -ui` |
| Kill processes on ports 8000 / 8888 | `python devcli.py -kui` |
| Clear simulation **disk + DB** workbench cache | `python devcli.py -csc` (same as `-cu`) |
| Clear **DB** workbench snapshot table only | `python devcli.py -cdc` |
| Delete strategy **`results/`** dirs only | `python devcli.py -cmc` |
| DuckDB WAL checkpoint | `python devcli.py -dbc` |

HTTP cache APIs: see [db-cache-service.md](core/modules/strategy/docs/db-cache-service.md) §8 (V2-11 / V2-12).

---

## Data

- The repo ships with a **small demo dataset** for a fast first run.
- For a **larger (~3-year) demo pack**, register on **[new-tea.cn](https://new-tea.cn)**, download the ZIP, clear **`setup/init_data/`**, place **one** zip there, then run `python setup/steps/import_data/install.py`.
- **Your own data source** (e.g. Tushare): [userspace/extensions/data_source/README.md](userspace/extensions/data_source/README.md).

---

## Documentation & website

- Official site (Chinese, richer docs): **[new-tea.cn](https://new-tea.cn)**
- Canonical README (Chinese): **[README.md](README.md)**
- Offline doc index: [docs/README.md](docs/README.md)

---

## Testing

```bash
python -m pytest
```

Please ensure tests pass before submitting a PR.

---

## License & disclaimer

This project is licensed under **Apache License 2.0** (see [LICENSE](LICENSE)).  
**Disclaimer**: for learning and research only, not investment advice; backtest results do not guarantee future performance.
