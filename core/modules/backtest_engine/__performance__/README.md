# Backtest Engine — 性能测试（`__performance__/`）

**模块：** `modules.backtest_engine`  
**用途：** 用**固定基准策略**测 BE 墙钟（entity / slice 分开测）。

| 命令 | 基准策略 | BE 模式 |
|------|----------|---------|
| `devcli.py bpe` / `be_perf_entity` | `test_strategies/be_perf_entity` | `entity_based` |
| `devcli.py bps` / `be_perf_slice` | `test_strategies/be_perf_slice` | `slice_based` |

两套策略万年不变（null hooks、不产出机会）；优化 BE 后分别对比墙钟才有意义。

## 数据（直接注入，无 CSV）

`db_creation.py` 建临时 DuckDB 后**直接写入**合成行：

- ID：`000000` … 连续编号
- 日历：周末休市，工作日开市
- K 线：固定规律 OHLC（测吞吐量够用）
- ST：不写（空表）

规模见 [`scripts/cmd/config.py`](./scripts/cmd/config.py)。fingerprint 一致则 `--reuse` 跳过重建。

## 目录

```text
__performance__/
├── README.md
├── CASES.md
├── scripts/
│   ├── test_strategies/       # 固定基准策略（勿随意改）
│   │   ├── be_perf_entity/
│   │   └── be_perf_slice/
│   └── cmd/
│       ├── db_creation.py     # 建库 + 直接注入
│       ├── run.py             # 跑单一 mode
│       ├── synthetic.py       # 合成行生成
│       ├── clean_up.py
│       └── …
├── .workdir/                  # 临时 DuckDB + registry（gitignore）
└── results/_local/            # 本地报告（gitignore）
```

## 如何运行

```bash
python devcli.py bpe          # entity_based
python devcli.py bps          # slice_based
python devcli.py bpc          # 清理生成物
```

或直接：

```bash
python core/modules/backtest_engine/__performance__/scripts/cmd/db_creation.py --reuse
python core/modules/backtest_engine/__performance__/scripts/cmd/run.py entity_based
python core/modules/backtest_engine/__performance__/scripts/cmd/run.py slice_based
```
