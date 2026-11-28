# Strategy — 用户指南

**模块：** `modules.strategy` · **版本：** `0.12.3`

**最低支持核心版本：** `>=0.5.0`

`Strategy 是策略执行核心——发现策略、加载配置、跑扫描和回测，把结果落到磁盘。`  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 自动发现 `userspace/strategies/` 下的策略，列出可以跑哪些
- 跑"扫描"：用最新行情找今天 / 上一交易日有哪些股票触发买入信号
- 跑"机会盘点"：回看历史某段时间，策略一共触发多少次机会
- 跑"回测"：在机会盘点之上再叠两层——单笔价格盈亏、组合资金曲线，看真实账户能不能赚钱
- 跑完产物自动落盘，带版本号和指纹缓存，配置没变就直接复用上次结果

## 配置说明

策略的用户可配项都在 `userspace/strategies/<你的策略>/settings.py`。下面是最常调的几组字段（全字段说明见 `userspace/strategies/settings_example.py`）：

| 配项 | 在哪配 | 默认值 | 说明 |
|------|--------|--------|------|
| `is_enabled` | settings.py 根级 | `False` | 是否被框架发现；忘了开列表里看不到 |
| `meta.key` | settings.py `meta` | 必填 | CLI `--strategy` 用的短名 |
| `core` | settings.py `core` | `{}` | 策略私有参数（阈值、窗口等），键名自定 |
| `data.base.data_key` | settings.py `data.base` | `stock.kline.daily` | 主时间轴数据（默认日 K） |
| `data.base.indicators` | settings.py `data.base` | `{}` | 要顺带算的技术指标（rsi / sma / macd 等） |
| `data.min_required_records` | settings.py `data` | `100` | 至少多少根历史 K 线才参与回测 |
| `data.stock_list_filter` | settings.py `data` | 无 | 按地域 / 行业 / 板块 / 交易所 / 上市状态过滤股票池 |
| `sampling` | settings.py `sampling` | 不采样 | 想先在小样本上快跑时开启 |
| `simulation.execution.start_date` / `end_date` | settings.py `simulation.execution` | 空=用全量数据范围 | 回测区间（YYYYMMDD） |
| `simulation.execution.mode` | settings.py `simulation.execution` | `entity_based` | 逐股跑还是按日历切片跑 |
| `goal.stop_loss` / `goal.take_profit` / `goal.expiration` | settings.py `goal` | 无 | 止损 / 止盈 / 最长持有天数 |
| `fees.commission_rate` | settings.py `fees` | `0.00025` | 佣金率（万 2.5） |
| `fees.min_commission` | settings.py `fees` | `5.0` | 单笔最低佣金 |
| `fees.stamp_duty_rate` | settings.py `fees` | `0.001` | 印花税（卖出收） |
| `simulation.assumption.tradability.slippage` | settings.py `simulation.assumption.tradability` | 进出场各 `5.0` bps | 进出场滑点 |
| `portfolio.initial_capital` | settings.py `portfolio` | `1_000_000` | 初始资金（100 万） |
| `portfolio.allocation.max_portfolio_size` | settings.py `portfolio.allocation` | `10` | 同时最多持几只 |
| `portfolio.allocation.max_weight_per_stock` | settings.py `portfolio.allocation` | `0.3` | 单票最大仓位权重 |
| `scanner.use_strict_previous_trading_day` | settings.py `scanner` | `True` | 数据没更到上一交易日时是否拒绝扫描 |

## 常见使用方式

### 场景 1：列一下当前发现了哪些策略

1. 仓库根目录跑 `python cli.py ls strategies`。
2. 输出里每行是一个策略（短名 + 显示名 + 路径）。
3. UI 路径：跑 `python launcher.py` 打开界面，点顶栏"制定策略"，列表里就是全部已启用的策略。
4. 看不到自己写的策略？先查 `settings.py` 里 `is_enabled` 是不是 `True`，目录是不是放在了 `_` 开头的目录下。

### 场景 2：跑一次扫描（找全市场机会）

1. 先把数据拉到最新：`python cli.py r`。
2. 跑扫描：`python cli.py c --strategy 你的策略key`；不带 `--strategy` 会把所有启用的策略都扫一遍。
3. 终端会列出每只股票命中信号的时间和关键读数。
4. UI 路径：顶栏"策略选股" → 选策略 → 点扫描，结果直接出表格。

### 场景 3：跑一次模拟（单策略回测）

1. 确认 `settings.py` 里 `simulation.execution.start_date` / `end_date` 已设好。
2. 一条命令跑三层：`python cli.py sim --strategy 你的策略key`（内部依次跑机会盘点 → 价格 → 组合）。
3. 想只跑某一层：分别用 `python cli.py se` / `sp` / `so --strategy 你的策略key`。
4. UI 路径：顶栏"制定策略" → 选策略 → 按 Stepper 三步（机会盘点 → 价格回测 → 组合模拟）逐一点运行。

### 场景 4：修改策略的配置（调回测区间、初始资金、分配方式）

1. 打开 `userspace/strategies/<你的策略>/settings.py`。
2. 改回测区间：改 `simulation.execution.start_date` / `end_date`；改初始资金：改 `portfolio.initial_capital`；改持仓数 / 单票权重 / 分配方式：改 `portfolio.allocation`。
3. 保存文件。
4. 重新跑 `python cli.py sim --strategy 你的策略key`——配置变了指纹就变，会自动重算并生成新版本，旧版本产物还在。
5. UI 路径：在"制定策略"详情页左侧设置面板改，保存等价于写回 `settings.py`。

### 场景 5：看回测产物（报告在哪、怎么看）

1. 优先在 UI 看：策略详情页下方就是本次运行的报告面板，能点开单只股票看 K 线和买卖点。
2. 磁盘产物在 `userspace/strategies/<策略路径>/results/simulations/{版本号}/`，分三层：
   - `enum/`：机会盘点出来的机会清单
   - `price/`：每只股两个 CSV（投资明细 + 目标达成）
   - `portfolio/`：组合层报告（`overall_report.json`、`equity_curve.json`、`trades.json`）
3. 同目录的 `meta.json` 是版本索引，列出每个版本对应的配置快照。

## 常见坑与注意事项

- **改了策略代码，跑回测还是旧结果：** 回测走指纹缓存——只要配置和代码没变化，框架直接复用上次结果。想强制重跑就加 `-f`（例如 `python cli.py sim -f --strategy xxx`）；UI 里对应"忽略缓存"开关。
- **settings 写错字段名没报错也没生效：** 配置是宽容解析，写错的键会被静默忽略。改完对照 `userspace/strategies/settings_example.py` 检查拼写和嵌套层级，特别是 `simulation.execution` 和 `portfolio.allocation` 这种多层结构。
- **扫描结果不全或干脆拒绝扫：** 严格模式（`scanner.use_strict_previous_trading_day=True`，默认开）要求本地数据已更到上一交易日。先跑 `python cli.py r` 拉数据；确实想接受旧数据，再把这个开关关掉。
- **列表里看不到刚写的策略：** 依次检查——`is_enabled: True`、`settings.py` 和 `strategy.py` 都在、目录不在 `_` 开头路径下（`_template/` 不参与发现）、目录名是字母开头的 ASCII。
- **跑出来的机会为 0：** 先看 `data.min_required_records` 是不是设太大（默认 100，新股或短时间窗容易全军覆没）；再把 `core` 里的阈值调松验证链路通不通。

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
