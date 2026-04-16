# New Tea Quant (NTQ) - A-Share Quant Research Framework

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.2.1-8A2BE2"></a>&nbsp;
  <a href="#"><img alt="Platform" src="https://img.shields.io/badge/platform-mac%20%7C%20linux%20%7C%20win-4CAF50"></a>&nbsp;
  <a href="#"><img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white"></a>&nbsp;
  <a href="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml"><img alt="Build" src="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml/badge.svg"></a>&nbsp;
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-007EC6"></a>
</p>

Author：Garnet Xin  

<a href="https://github.com/garnet1985/new-tea-quant"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-new--tea--quant-181717?logo=github&logoColor=white"></a>&nbsp;
<a href="https://gitee.com/garnet/new-tea-quant"><img alt="Gitee" src="https://img.shields.io/badge/Gitee-new--tea--quant-C71D23?logo=gitee&logoColor=white"></a>&nbsp;
<a href="https://new-tea.cn"><img alt="Website" src="https://img.shields.io/badge/website-new--tea.cn-009688?logo=google-chrome&logoColor=white"></a>

<br/>

> **Tip:** This is a short English introduction of the project. For the full and always up‑to‑date documentation, please also refer to the Chinese README and the official site.

### What is NTQ?

**NTQ (New Tea Quant)** is a local, single‑machine quantitative research framework for A‑share strategies.  
It focuses on helping you **verify trading ideas quickly**, and then **apply the same logic to real‑time market data** to enumerate opportunities.

Examples of ideas you can validate:

- "Is weekly RSI < 20 a good entry signal?"
- "Do MACD golden / dead crosses really work on my universe?"
- "What is the win rate of chasing 'hot' stocks under my own rules?"

NTQ provides:

- A **strategy research framework** (multi‑process / multi‑threaded)  
- Detailed **logs and intermediate values** so that every result is traceable and reproducible  
- The ability to **plug in your own data source** and **your own notification / trading layer**

> NTQ itself is free and open source (Apache 2.0). Some capabilities (data, notifications, trading) require you to integrate third‑party platforms or APIs by yourself.

### Tech stack

- **Language**: Python 3.9+
- **Database**: PostgreSQL or MySQL
- **License**: Apache 2.0

---

## Quick start (run in ~5 minutes)

### 1. Clone the repo

```bash
git clone https://github.com/garnet1985/new-tea-quant.git
cd new-tea-quant
```

### 2. Configure database

Create a new database (either MySQL or PostgreSQL), then configure:

- In `userspace/config/database`:
  - Copy `common.example.json` to `common.json`, and set database type.
  - Copy the corresponding DB config file (e.g. `mysql.example.json` → `mysql.json`) and fill in database name, user, password, host, port, etc.

### 3. Install & verify

```bash
python install.py
```

After installation succeeds, run the built‑in `example` strategy:

```bash
python start-cli.py -sp
```

If you see results printed in the terminal, the framework is up and running.

### More common commands

```bash
python start-cli.py -h      # show help
python start-cli.py -sa     # simulate with capital
python start-cli.py -t      # generate labels / features
```

Default command entry is always `start-cli.py`.  
If you see `start.py` mentioned in older docs, treat `start-cli.py` as the source of truth.

---

## Data

- The repo ships with a **small demo dataset** to help you get started quickly.  
- For a **larger (3‑year) demo dataset**, please register and download it from the official site, then put the zip file under `setup/init_data` and rerun `python install.py`.
- You can also **connect your own data source** (for example Tushare); see `userspace/data_source/README.md` for details.

---

## Documentation & website

- Official site (Chinese, with more detailed docs and examples): `https://new-tea.cn`
- Root Chinese README: `README.md` (the canonical entry for docs)

---

## Testing

```bash
python -m pytest
```

Please ensure tests pass before submitting a PR.

---

## License & disclaimer

This project is licensed under **Apache License 2.0** (see `LICENSE`).  
**Disclaimer**: for learning and research only, not investment advice; backtest results do not guarantee future performance.

