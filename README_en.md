# New Tea Quant (NTQ) — Quantitative Research Framework for A-Shares

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.4.5-8A2BE2"></a>&nbsp;
  <a href="#"><img alt="Platform" src="https://img.shields.io/badge/platform-mac%20%7C%20linux%20%7C%20win-4CAF50"></a>&nbsp;
  <a href="#"><img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white"></a>&nbsp;
  <a href="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml"><img alt="Build" src="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml/badge.svg"></a>&nbsp;
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-007EC6"></a>
</p>

> For the Chinese introduction, see **[here](README.md)**.

Author: Garnet Xin & his AI companions

<a href="https://github.com/garnet1985/new-tea-quant"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-new--tea--quant-181717?logo=github&logoColor=white"></a>&nbsp;
<a href="https://gitee.com/garnet/new-tea-quant"><img alt="Gitee" src="https://img.shields.io/badge/Gitee-new--tea--quant-C71D23?logo=gitee&logoColor=white"></a>&nbsp;
<a href="https://new-tea.cn"><img alt="Website" src="https://img.shields.io/badge/website-new--tea.cn-009688?logo=google-chrome&logoColor=white"></a>

Skip the intro and install now? See [Quick install + run a strategy](#quick-start). Other jumps: [Why NTQ](#why) · [Star the project](#star) · [CLI](#cli) · [Tutorials](https://new-tea.cn/zh-hans/more-examples) · [Website](https://new-tea.cn)

## Current version (v0.4.x)

Recent updates:

**[v0.4.5](CHANGELOG.md)**

- **Backtest attribution:** explain how single factors (statistics) and multiple factors (machine learning) contributed to a run.
- Full list: [CHANGELOG.md](CHANGELOG.md).

**Next**

- **[v0.5.x](ROADMAP.md):** Decision-maker mode (fourth backtest layer: replay trading days and pick opportunities yourself) plus its reports.
- **[v0.5.x](ROADMAP.md):** AI assistant (help write strategy code, explain reports, in-app handbook).
- See [ROADMAP.md](ROADMAP.md).

## What is NTQ?

**New Tea Quant** (NTQ) is a personal-developer-friendly, lightweight, high-performance framework for quantitative strategy backtesting and research. (**New Tea** is named after the author’s British Shorthair; her name is “新茶” / New Tea.)

NTQ does two things:

- Help you turn the stock-picking and trading ideas in your head into code, then test them on historical data.
- Run that same stock-picking logic on the latest market, find opportunities, and report them to you.

There is more. See [What else can NTQ do?](#can).

<a id="star"></a>
## Star NTQ

If you like NTQ and want to support it, please star the project on [GitHub](https://github.com/garnet1985/new-tea-quant) or [Gitee](https://gitee.com/garnet/new-tea-quant). Your support is what keeps the author going.

Bugs and ideas are welcome too — leave a note on the [website contact form](https://new-tea.cn/zh-hans/contact). Full channels: [How to participate](#participate).

<a id="why"></a>
## How is NTQ different? Why use it?

The author wanted to do his own quant research. Off-the-shelf tools did not fit well enough, so he built a research stack around a personal PC and China A-shares.

- **NTQ tries to dodge these traps for you by default.**

  > Ever wonder why a strategy looks like the hottest thing in a backtester, then gets crushed live? Often because:

  - **Your data may have survivorship bias.** The names on stock websites are the ones still alive. Did your backtest include names that later delisted? Buying those can produce huge losses. Leave them out and your returns and win rate look better than they should.

  - **Did you peek at future data?** If you reconstruct a moment in the middle of the timeline from the complete history, you may have used information that did not exist yet to justify a decision at that moment. Live trading cannot do that, so the backtest is often distorted. NTQ uses data contracts to keep future data out of reach: you cannot pull from backtest data or the context object anything that would only exist later, including event times. A conclusion at T strictly follows data that was already known at T.

  - **Do you know how adjusted prices are built?** How they differ from raw prices? If your backtest uses adjusted prices for P&L and stop/take-profit, it is almost certainly wrong. Forward-adjusted prices can make position sizing too optimistic. In extreme cases they can go **negative**; a simulated buy at a negative price makes return negative whether you actually lost money or not. Did you catch that?

  - **Even if the strategy is profitable, is it a handful of extreme names — or is everyone grinding up?** How do you choose when several opportunities appear on the same day? Can you persist intermediate data and inspect it later? After a run, do you know the shape of the return distribution? Without that, you cannot really find a strategy that fits you.

  - **Even a “working” strategy may not fit you.** What if it needs an 80% drawdown to chase 200%? Can you live with that? Can you still follow the rules when only 20% of capital is left? Or would you rather risk 10% to make 20%? NTQ’s decision-maker mode (**[v0.5.x](ROADMAP.md)**, coming soon) replays dates and positions so you can sit in the seat and pick something you can actually stick with.

  - **Many tools backtest each stock on its own.** What if stocks depend on each other — e.g. invest in today’s top-5 volume names? Per-stock loops get messy and slow. NTQ supports both independent per-stock runs and calendar **slice** mode: no cross-name dependency, and it runs like most frameworks; if there is dependency, add one filter function and slice mode still keeps it efficient.

  - **Is one backtest pass enough?** Return, win rate, and Sharpe are not a verdict. NTQ plans **four layers**. Layer 1 — **opportunity enumeration**: how many hits in a huge universe, scattered or concentrated? Layer 2 — **price-factor backtest**: can the rules capture a name’s price move under some risk? Layer 3 — **portfolio simulation**: starting capital, human-like trading, final P&L and its distribution. Layer 4 — **decision-maker** (**[v0.5.x](ROADMAP.md)**): replay the calendar, pick daily opportunities yourself, and see if you can keep discipline, live with the risk, and still finish in profit. The UI can run the first three layers today.

There are many smaller traps. NTQ’s engine ships tradability modules so you get a result you can trust — not a script thrown at random data.

- **NTQ is tuned for a personal PC.** Other desktop backtesters leave memory management to you. A large dataset can freeze or bluescreen a laptop. NTQ schedules CPU and memory during a run so a PC can backtest more data than fits in RAM, without giving up all speed.

- **NTQ is built for the China market.** Popular frameworks usually start from US / overseas markets and get “ported” to A-shares — with plenty of pitfalls. NTQ started from A-shares.

- **NTQ is declarative.** You write less code; most of the work is JSON-like config. A strategy is two files: `strategy.py` and `settings.py`.

In **`settings.py`** you can configure most of the backtest:

- Trading basics
- Risk controls
- Goals
- Data the run needs
- Universe
- …

Full field notes: `userspace/strategies/settings_example.py` (created after install).

<details>
<summary><strong>settings.py examples (click to expand)</strong></summary>

A simple goal: take profit at +30%, stop at −20%:

```python
"goal": {
    "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
    "take_profit": {"stages": [{"ratio": 0.3, "close_invest": True}]},
}
```

A multi-stage goal that changes as P&L moves: hold at most 100 trading days, stop at −20%. At +15% raise the stop to cost. At +30% sell half. At +50% sell another 40%, leave 10% on a trailing stop that exits if drawdown exceeds 15%:

```python
"goal": {
    "expiration": {"fixed_window_in_days": 100, "mode": "trading_day"},
    "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
    "take_profit": {
        "stages": [
            # +15%: do not sell; lift stop to cost
            {"ratio": 0.15, "exit_ratio": 0, "actions": ["set_protect_loss"]},
            # +30%: sell half of current size (50% of original)
            {"ratio": 0.3, "exit_ratio": 0.5},
            # +50%: sell 40% more; remaining 10% goes to trailing stop
            {"ratio": 0.5, "exit_ratio": 0.4, "actions": ["set_dynamic_loss"]},
        ]
    },
    "protect_loss": {"ratio": 0, "close_invest": True},
    "dynamic_loss": {"ratio": -0.15, "close_invest": True},
}
```

Inject daily bars, quarterly fundamentals, and CPI:

```python
"data": {
    "base": {
        "data_key": "stock.kline.daily",
        "params": {"adjust": "qfq"},
    },
    "required": [
        {"data_key": "stock.finance.quarterly"},
        {"data_key": "macro.cpi"},
    ],
}
```

Add MACD on the base K-line:

```python
"data": {
    "base": {
        "data_key": "stock.kline.daily",
        "params": {"adjust": "qfq"},
        "indicators": {
            "macd": [{"fast": 12, "slow": 26, "signal": 9}],
        },
    },
}
```

</details>

---

In **`strategy.py`**, entry on a single name is just `has_opportunity` (see the installed demo **RSI超跌反弹v1**). Slice filters, portfolio picks, and custom goals are optional:

- **`has_opportunity(ctx)`:** is there a buy today for this stock? You see data **as of today**. Return `True` / `False` (`False` skips).
- **`on_calendar_asof(ctx)`:** for **`slice_based`** mode. You see the full universe as of today, filter first, return stock ids; then `has_opportunity` runs on those ids.
- **`on_pick_portfolio_member(ctx)`:** capacity. E.g. max 3 holdings but 10 hits today — choose which 3.

You can also customize goals: put `"custom": "rule_name"` on a take-profit / stop-loss stage in `settings.py`, then implement **`is_take_profit`** / **`is_stop_loss`**.

<details>
<summary><strong>strategy.py hook examples (click to expand)</strong></summary>

```python
# Example: RSI below 20 counts as an opportunity:
def has_opportunity(self, ctx: StrategyContext) -> bool:
    # Daily bars for this name as of today (plus declared indicators); last row is today
    klines_daily = ctx.data.items.get("stock.kline.daily") or []
    if not klines_daily:
        return False
    # Last bar in the series is today
    kline_today = klines_daily[-1]
    # RSI from today's bar
    rsi = kline_today.get("rsi14")
    # Optional: record today's RSI for later attribution
    ctx.capture("rsi", rsi)

    # True = there is an opportunity when RSI exists and is below 20
    # In practice this 20 lives in settings.core so the UI can show it and you can vary the parameter
    return rsi is not None and rsi < 20
```

- **`on_calendar_asof(ctx)`:** `slice_based` only. You see the full universe as of today, filter first; put the selected stock ids in `CalendarAsOfResult`, then `has_opportunity` runs on those ids.

```python
# Example: pick the 3 names with the highest turnover today, then hand them to has_opportunity
def on_calendar_asof(self, ctx: StrategyContext) -> CalendarAsOfResult:
    today = str(ctx.data.now or "")
    ranked = []

    # ctx.data.by_entity: every name in the universe, data as of today
    for stock_id, payload in (ctx.data.by_entity or {}).items():
        # Turnover is on daily indicators; declare stock.indicators.daily in settings.data.required
        rows = payload.get("stock.indicators.daily") or []
        if not rows:
            continue
        # Last row is today
        indicator_today = rows[-1]
        turnover = indicator_today.get("turnover_rate")
        if turnover is None:
            continue
        ranked.append((turnover, stock_id))

    # Highest turnover first, take top 3
    ranked.sort(reverse=True)
    top3 = [stock_id for _, stock_id in ranked[:3]]

    # CalendarAsOfResult: tell the framework which names you screened today
    return CalendarAsOfResult(as_of_date=today, stocks=top3)
```

- **`on_pick_portfolio_member(ctx)`:** capacity. E.g. max 3 holdings but 10 hits today — choose which 3.

```python
# Example: when there are many hits today, buy the 3 highest-priced names
def on_pick_portfolio_member(self, ctx: StrategyContext):
    # Opportunities scanned today that are not yet in the book
    opportunities = ctx.data.items.get("opportunities") or []
    # How many slots are left (open holdings already occupy slots)
    remaining = (ctx.data.items.get("account") or {}).get("remaining_slots") or 0

    ranked = []
    for opp in opportunities:
        # trigger_price: signal price for this name today (usually close)
        price = opp.trigger_price
        ranked.append((price, opp))

    # Highest price first, take top 3, and do not exceed remaining slots
    ranked.sort(key=lambda item: item[0], reverse=True)
    n = min(3, remaining)
    return [opp for _, opp in ranked[:n]]
```

Custom take-profit / stop-loss: put `"custom": "rule_name"` on a stage in `settings.py`; the framework then asks `is_take_profit` / `is_stop_loss` whether to fire today.

```python
# settings.py: this take-profit stage has no fixed ratio; strategy.py decides. close_invest = flatten the whole position
"take_profit": {"stages": [{"custom": "up_20pct", "close_invest": True}]}

# strategy.py
# Example: take profit when the name is 20% above entry
def is_take_profit(self, ctx: StrategyContext, *, custom: str, stage) -> bool:
    if custom != "up_20pct":
        return False

    # While a position is open, the framework hands you today's bar directly
    bar = ctx.data.items.get("bar") or {}
    close = bar.get("close")
    # Fill price at entry
    entry_price = ctx.data.items.get("entry_price") or 0
    if close is None or not entry_price:
        return False

    return close >= entry_price * 1.2
```

`is_stop_loss` is the same pattern; put the rule on `stop_loss.stages`.

</details>

### How NTQ differs from other platforms

Compared with common open-source backtesters (any market): [Backtrader](https://www.backtrader.com/), [Zipline](https://github.com/stefan-jansen/zipline-reloaded), [vectorbt](https://vectorbt.dev/), [backtesting.py](https://kernc.github.io/backtesting.py/).

| | **NTQ** | **Backtrader** | **Zipline** | **vectorbt** | **backtesting.py** |
| --- | --- | --- | --- | --- | --- |
| Focus | A-share research + scan on a PC | Event-driven general backtest | Pipeline research backtest | Fast vectorized / factors | Light single-name event backtest |
| Full-market on a laptop | CPU + memory scheduling to avoid OOM | You manage memory | Very RAM-heavy | Fast, but matrices still eat RAM | Single-name first; wrap it yourself for the universe |
| Default market mind | Starts from A-shares | Generic; US-like defaults | US / USD mind | Market-agnostic; bring data | Market-agnostic; bring data |
| Delisting / survivorship | PIT universe by default | Whatever you feed | Official packs are decent; DIY data is on you | Whatever you feed | Whatever you feed |
| Signal vs fill price | Adjusted for signals, raw for fills | Uses whatever you feed | Often adjusted series; dual track is DIY | Uses whatever you feed | Uses whatever you feed |
| Cross-section (e.g. Top-N) | Native slice mode | Usually loop the universe | Pipeline can; not easy | Matrices shine; tradability is extra | Weak at full-market cross-section |
| How the backtest is split | Enumerate → price → capital → decision-maker | Typically one NAV curve | Typically one research run | One vectorized run | Typically one NAV curve |
| Decision-maker (sit in the seat) | **[v0.5.x](ROADMAP.md)** coming | No | No | No | No |
| Web reports / per-stock path | Built-in workbench | Draw it yourself | Research notebooks | Jupyter / DIY | Simple charts included |

<a id="participate"></a>
### How to participate (pick one)

| Channel | Best for |
|------|------|
| [GitHub Issues](https://github.com/garnet1985/new-tea-quant/issues) | Bugs & features (easiest to track) |
| [Gitee Issues](https://gitee.com/garnet/new-tea-quant/issues) | Bugs & features (easiest to track) |
| [Website contact](https://new-tea.cn/zh-hans/contact) | Form, no account required |
| GitHub / Gitee DMs | Short or private notes |

When you file an issue, **OS (Win / macOS / Linux), Python version, which step, screenshot or error summary** speeds things up a lot. See also [CONTRIBUTING.md](CONTRIBUTING.md) · [SUPPORT.md](SUPPORT.md).

## What skills do you need?

NTQ helps you test your ideas. You will likely need:

- Know basic financial terms and market rules
- A way to turn “this looks like a promising name” into an algorithm (**[v0.5.x](ROADMAP.md)** AI help; not in this version)
- Enough Python to turn that idea into code (**[v0.5.x](ROADMAP.md)** AI coding help; not in this version)
- Enough stats to read a basic backtest report (**[v0.5.x](ROADMAP.md)** AI report help; not yet)

## What NTQ cannot do

NTQ is a backtester. It does not provide:

- **A stable live data feed** (you connect your own). The repo ships ~3 years / **300** names of demo data; after you register you can download a ~3-year **full A-share** pack from the [member page](https://new-tea.cn/zh-hans/user/) (see [Data notes](#data)).
- **Live brokerage trading.** There is no broker hook. Scan results go out through the [`adapter`](core/modules/adapter/README.md) module. If you can talk to a third-party trading app or venue, you can pass those opportunities downstream.

## How do I run it?

No required third-party services. With [Python](https://new-tea.cn/zh-hans/install-python) ≥ 3.9, clone and run — spend time on strategies, not glue.

For most users: download the code, `cd` to the NTQ root, run:

```bash
python launcher.py
```

Then finish install in the UI.

Developers: prefer [**MySQL**](https://dev.mysql.com/downloads/) or [**PostgreSQL**](https://www.postgresql.org/download/), which you install yourself.

Full walkthrough: [Quick install + run a strategy](#quick-start).

<a id="can"></a>
## What else can NTQ do?

- **Talk to the database quickly:** [DuckDB](https://duckdb.org/), [MySQL](https://dev.mysql.com/), and [PostgreSQL](https://www.postgresql.org/), plus a small [ORM API](core/infra/db/README.md).
- **Custom data sources:** a full ingest toolkit. One logical source (e.g. company fundamentals) can have several vendors, with rate limits, waits, and write modes (incremental, overwrite, rolling refresh). See [core/modules/data_source/README.md](core/modules/data_source/README.md).
- **Custom data contracts:** most of the run is config. If you add a table and want it in the backtest by declaration, give it a unique `data_key` and a loader; the framework finds the loader by name. See [data contracts](core/modules/data_contract/README.md).
- **Attribute a backtest:** which parameters actually moved the result, and by how much? The ML attribution module speaks to that. It only explains **this** run; a different universe, window, or layer can tell a different story — watch the scope so you do not overfit. Shortest UI path: [Quick Start](#attribution).
- **Adapters:** after a scan, wire [`adapter`](core/modules/adapter/README.md) to your own downstream (notifications, a trading app, anything). You get standard opportunity payloads plus backtest history if you have run one.
- **Web UI:** use it in the browser. Visualize results and compare inputs/outputs across runs so you can tune the strategy on purpose.
- **CLI:** [`python cli.py`](#cli) lists commands.
- **Markets:** China A-shares are fully supported today. [`market_profile`](core/modules/market_profile/README.md) is the door to other markets; more will come.

### Please note

NTQ itself is free and open source. Some capabilities need **your** resources:

- **Data:** ingest and storage are in the framework; **paid vendor accounts / tokens are not**. Register and buy those yourself.
- **Notifications:** SMS / email / push are **not** in the framework. Hook them via an [adapter](core/modules/adapter/README.md).

Fuller tutorials (Chinese): [More examples](https://new-tea.cn/zh-hans/more-examples). License: [Apache 2.0](LICENSE) ([License & support](#license)).

<a id="quick-start"></a>
## Quick install + run a strategy

Goal: **framework up + one demo strategy in about 5 minutes**.

### Prerequisites

- **Python 3.9+**. If needed: [Install Python](https://new-tea.cn/zh-hans/install-python).
- **Developers:** install [Node.js](https://nodejs.org/) (for UI work); prefer [MySQL](https://dev.mysql.com/downloads/) or [PostgreSQL](https://www.postgresql.org/download/). ([DuckDB](https://duckdb.org/) single-writer mode is awkward while debugging.)

### Step 1: Get the code

Pick one.

- **Git clone** (recommended), GitHub or Gitee:

```bash
git clone https://github.com/garnet1985/new-tea-quant.git
cd new-tea-quant
```

```bash
git clone https://gitee.com/garnet/new-tea-quant.git
cd new-tea-quant
```

- **Download ZIP:** on [GitHub](https://github.com/garnet1985/new-tea-quant) or [Gitee](https://gitee.com/garnet/new-tea-quant) use **Code → Download ZIP**, unzip, enter the **`new-tea-quant`** root (same folder as [`launcher.py`](launcher.py)).

### Step 2: Start the setup wizard from the repo root

In the **project root** (where `launcher.py` is):

```bash
python launcher.py
```

Windows PowerShell:

```bash
python .\launcher.py
```

If `python` is an old version:

```bash
python3 launcher.py
```

The script switches to the repo root, ensures the venv, then **starts BFF + frontend and opens the browser** into the graphical **Setup wizard** (BFF setup API).

### Step 3: Finish initialization in the browser

Follow the prompts; defaults are usually enough. Order is roughly:

1. Install core Python deps
2. Initialize `userspace`
3. Configure the database (default **DuckDB**; developers can pick MySQL / PostgreSQL — the app will try to create a missing database and warn on name clashes)
4. **Ask whether to import demo data** (skippable; you can connect your own source later)
5. **Ask whether to install ML extras** (for attribution; skippable; later: **设置 → 安装与维护**)
6. Usage stats (allow or decline; both continue)

You land on the **welcome page**. Then use the nav item **制定策略** (Strategy Design).

That completes NTQ installation.

### Step 4: Run a demo

Bundled demo assets:

- **Data:** about **2023-01 ~ 2025-12**, **300** stocks (three years). Not for commercial use.
- **Strategies:** default demos only — do not trade live off them.

#### Open the strategy UI

In the UI click **制定策略**, or open `/strategy-design/`. Pick a demo (e.g. **RSI超跌反弹v1 · 基线**), then the title or **进入调试**:

![Fig. 1: Navigate to Strategy Design](docs/images/demo/1.jpg)

![Fig. 2: Strategy list](docs/images/demo/2.jpg)

![Fig. 3: Strategy detail](docs/images/demo/3.jpg)

Four main areas:

- **Strategy info:** top full-width block — name, description, version capsule, pin / restore.
- **Strategy settings:** left panel; changes with each backtest step. Saving writes `settings.py`. A new disk version is allocated when the execute fingerprint changes.  
  **Note:** Strategy **logic** cannot be edited in the UI — only under `userspace/strategies/`. The UI only tunes parameters exposed in code. (**[v0.5.x](ROADMAP.md)** will add AI assistance.)
- **Execution panel:** run the current step. Three stages today (decision-maker is **[v0.5.x](ROADMAP.md)**):  
  - **Enumerate:** find historical opportunities;  
  - **Price backtest:** 1 share, ignore costs — price-capture quality;  
  - **Portfolio:** starting capital, sizing, risk controls — closer to real trading.
- **Reports:** auto-generated per step.

<a id="attribution"></a>
For **attribution write-ups:** install ML extras in the wizard (or later under **设置 → 安装与维护**), turn on **归因分析** in global settings, then run. The write-up appears under the report. More: [More examples](https://new-tea.cn/zh-hans/more-examples).

#### Stage 1: Opportunity enumeration

After enumeration, reports usually split into **per-stock** and **global** (later stages follow the same idea):

![Fig. 4: Enumeration report (per-stock + global)](docs/images/demo/4.jpg)

Click a row to open that stock’s chart — K-lines, indicators, and opportunity markers (e.g. blue dots):

![Fig. 5: Single-stock chart with opportunity marks](docs/images/demo/5.jpg)

Below the list, the global enum report summarizes where opportunities cluster, average duration, and similar diagnostics:

![Fig. 6: Enumeration global report](docs/images/demo/6.jpg)

#### Stage 2: Price backtest

Focuses on price-capture quality. The single-stock view shows entries/exits — not P&L drama, but clear timing for debugging:

![Fig. 7: Price backtest chart (entries/exits)](docs/images/demo/7.jpg)

The global report covers buy/sell price distributions, returns, and more — always read it against your configured goals:

![Fig. 8: Price backtest global report](docs/images/demo/8.jpg)

#### Stage 3: Portfolio simulation

Closer to real trading: capital, positions, risk settings, and a historical simulation of whether the strategy can actually make money.  
(Portfolio reports do not support per-stock drill-down; enumerate and price backtest do.)

![Fig. 9: Portfolio global report](docs/images/demo/9.jpg)

![Fig. 10: Equity / drawdown style curves](docs/images/demo/10.jpg)

#### Strategy scan: finding live-market opportunities

When a strategy is tuned, use **策略选股** (Strategy Scan) from the main nav.

Scans use the current `settings.py` in the strategy folder (the workbench Persist / Run path writes that file). There is no separate **Publish strategy** step.

For a “real” market scan you typically need:

- **Fresh enough data** (NTQ does not ship a vendor; connect your own — [data_source module](core/modules/data_source/README.md))
- An **enabled, complete** strategy

On the scan page you can use **严格模式** (strict: refuse to run if data is stale), pick a strategy, and click **开始扫描**. Results list current opportunities:

![Fig. 11: Strategy scan](docs/images/demo/11.jpg)

For a dry run only, choose **扫描演示**. The app pretends “today” is the day after your local data’s last trading day, then runs at that synthetic as-of.

That is a simple path from backtest to scan — there is more in NTQ to explore.

<a id="data"></a>
## Data notes

1. For a **larger (~3 years, full A-share) package**: [register and sign in on the member page](https://new-tea.cn/zh-hans/user/), download it, leave **only one** zip under [`initialization/data/`](initialization/data/) (move the old demo zip aside), then run `python cli.py id` (`-f` forces a full re-import; see [CLI](#cli)). You can point a different DB name to keep demo and full data side by side (after install: `userspace/system/config/database/`).
2. **Bring your own data source** (e.g. [Tushare](https://tushare.pro)): see [core/modules/data_source/README.md](core/modules/data_source/README.md).
3. Demo data and strategies are for learning/research only — not live trading or commercial use.

## Disclaimers

This is still unofficial **v0.x**: API stability is not guaranteed until 1.0. (Before 1.0, APIs are at most beta.) See [CHANGELOG.md](CHANGELOG.md).

<a id="cli"></a>
## Common commands (`cli.py`)

Layered backtest and scan (full list: `python cli.py -h`):

```bash
python cli.py se --strategy rsi_v1   # Enumerate
python cli.py sp --strategy rsi_v1   # Price layer
python cli.py so --strategy rsi_v1   # Portfolio layer
python cli.py s  --strategy rsi_v1   # All three layers
python cli.py sa --strategy rsi_v1   # Latest attribution for that step (--version optional)
python cli.py c  --strategy rsi_v1   # Market scan
python cli.py t  --scenario demo/market_cap_tier   # Feature tags
```

Prefer an explicit `--strategy`; add `-f` to force recalculation. Demo Tag scenario after install: `userspace/extensions/tags/demo/market_cap_tier/`.

---

## Typical use cases

| Goal | Suggested path |
|------------|----------|
| **Does this signal fire?** | Web **制定策略** (see [Quick Start step 4](#quick-start)) → demo → **enumerate** → count & distribution |
| **Does a trigger capture price?** | After enum → **price backtest** → click a stock for entries/exits |
| **Survive with limited capital?** | After price layer → **portfolio simulation** → curves & holdings |
| **Monthly low-price / Top N across A-shares** | After install: `userspace/strategies/demo/cross_sectional/low_price/`, **`slice_based`** mode |
| **Share one factor across strategies** | Run **[Tag](core/modules/tag/README.md)** ([`cli.py t`](#cli)), reference it in settings |
| **Screen with latest bars** | Refresh data → [`cli.py c`](#cli) or Web scan (notify via [Adapter](core/modules/adapter/README.md)) |

---

<a id="upgrade"></a>
## Upgrade

1. Pull latest **master**, **keep** `userspace/` (created at install — do not overwrite it on upgrade); overwrite the rest.  
2. Daily UI: `python launcher.py` (installs UI deps if needed). CLI / Python deps only: [`python install.py`](install.py). Upgrade an installed app: `python cli.py u`. If [release notes](CHANGELOG.md) ask for a data re-import, see [Data notes](#data).

---

<a id="license"></a>
## License & support

- **License:** [Apache 2.0](LICENSE) · **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **Feedback / contribute:** [SUPPORT.md](SUPPORT.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)
- **Website:** [new-tea.cn](https://new-tea.cn) · **Tutorials:** [More examples](https://new-tea.cn/zh-hans/more-examples)

**Disclaimer:** For learning and research only. Not investment advice; backtests do not predict future results.

<details>
<summary>Developer appendix (branches, devcli, tests, docs)</summary>

**Layout:** [`core/`](core/) framework · `userspace/` strategies & config (created at install, kept on upgrade) · demos after install under `userspace/strategies/demo/` · [docs/README.md](docs/README.md)

**Branches:** `master` for releases; branch `feature/*` / `bugfix/*` from `dev`; `hotfix/*` only from `rc`. Do not PR straight to `master`.

**Dev:** `python devcli.py -h` (`ui` · `uk` · `csc`) · Docker: [docs/docker.md](docs/docker.md)

**Tests / deps:**

```bash
./venv/bin/python -m pytest   # pip install -r requirements-dev.txt first
python3 -m piptools compile --output-file requirements.txt requirements.in
```

Dep lists: [requirements-dev.txt](requirements-dev.txt) · [requirements.in](requirements.in)

</details>

---

## Fun time: How do AIs rate NTQ?

> Third-party AI comments after reading some NTQ core files/docs — **for fun**, with **full reply screenshots**. **Not ads**, not official AI positions; models can be overly optimistic — judge from the repo yourself.  
> You are welcome to ask your own AI; make it read core code first, or expect severe hallucinations.

<details>
<summary><strong>Gemini 3.1 Pro</strong> (expand)</summary>

![Gemini 3.1 Pro review of NTQ](docs/images/ai-assessments/gemini-3.1-pro.jpg)

</details>

<details>
<summary><strong>GPT-5.5</strong> (expand)</summary>

![GPT-5.5 review of NTQ](docs/images/ai-assessments/gpt-5.5.jpg)

</details>

<details>
<summary><strong>Claude Sonnet 4.6</strong> (expand)</summary>

![Claude Sonnet 4.6 review of NTQ](docs/images/ai-assessments/claude-sonnet-4.6.jpg)

</details>

<details>
<summary><strong>DeepSeek</strong> (expand, 6 screens stitched)</summary>

![DeepSeek review of NTQ](docs/images/ai-assessments/deepseek.jpg)

</details>

<details>
<summary><strong>Gitee Assistant</strong> (expand)</summary>

![Gitee Assistant review of NTQ](docs/images/ai-assessments/gitee-assistant.jpg)

</details>
