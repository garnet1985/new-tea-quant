# 回测引擎 — 性能测试（`__performance__/`）

用**固定空策略**测引擎跑得有多快（按股票分包 / 按时间切片 **分开测**）。

| 命令 | 测哪一种 | 策略目录 |
|------|----------|----------|
| `devcli.py bpe` | 按股票分包（entity） | `test_strategies/entity_based` |
| `devcli.py bps` | 按时间切片（slice） | `test_strategies/slice_based` |
| `… --db mysql` | 同上，改用 MySQL | 读 userspace 的 mysql 配置 |
| `… --db pgsql` | 同上，改用 PostgreSQL | 读 userspace 的 postgresql 配置 |
| `… --db pgsql` | 同上，改用 PostgreSQL | 读 userspace 的 postgresql 配置 |

两套策略固定不变（不选股、不产生交易机会）；优化引擎后分别对比**总执行时间**才有意义。两种模式不要直接比谁更快。

## 数据（直接写入，无 CSV）

`db_creation.py` 建临时库后**直接写入**合成行情：

- 股票编号：`000000` … 连续编号
- 日历：周末休市，工作日开市
- K 线：固定规律价格（测快慢够用）
- ST：不写（空表）

规模见 [`scripts/cmd/config.py`](./scripts/cmd/config.py)。数据规模没变时，`--reuse` 会跳过重建。

## 目录

```text
__performance__/
├── README.md
├── CASES.md
├── reports/
│   ├── test_preconditions.md  # 测试前提（机器 / 数据 / 跑法 / 报告）
│   ├── REPORT_TEMPLATE.md     # 给人看的报告字段说明
│   └── {BE版本}/              # 留档：模式 × 数据库
├── scripts/
│   ├── test_strategies/       # 固定空策略（勿随意改）
│   │   ├── entity_based/
│   │   └── slice_based/
│   └── cmd/
│       ├── db_creation.py     # 建库 + 直接写入（duckdb / mysql / postgresql）
│       ├── mysql_support.py   # MySQL 探测 / 安全建删库
│       ├── postgresql_support.py  # PostgreSQL 探测 / 安全建删库
│       ├── run.py             # 跑一种模式
│       ├── synthetic.py       # 合成行情
│       ├── clean_up.py
│       └── …
├── .db/                       # 临时库（gitignore）
└── results/_local/            # 旧本地草稿（gitignore；正式报告在 reports/{版本}/）
```

## 如何运行

```bash
python devcli.py bpe              # 按股票分包（默认 duckdb）
python devcli.py bps              # 按时间切片
python devcli.py bpe --db mysql   # MySQL（需 userspace 配置）
python devcli.py bps --db pgsql   # PostgreSQL（需 userspace 配置）
python devcli.py bpc              # 清理临时库和本地结果
```

或直接：

```bash
python core/modules/backtest_engine/__performance__/scripts/cmd/db_creation.py --reuse
python core/modules/backtest_engine/__performance__/scripts/cmd/run.py entity_based
python core/modules/backtest_engine/__performance__/scripts/cmd/run.py slice_based
```

测试前提见 [`reports/test_preconditions.md`](./reports/test_preconditions.md)。
