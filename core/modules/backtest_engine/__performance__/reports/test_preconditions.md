# BE 性能测试前提

本轮在 **macOS** 上跑。**当前能跑的只有 DuckDB**（`bpe` / `bps` 默认即此）。  
`--db mysql` / `--db pgsql` 已在命令行预留，但建库注入尚未实现，会直接报错退出。报告里必须写明这次用的数据库类型。

---

## 1. 机器

| 项 | 值 |
|----|-----|
| 系统 | macOS 15.7.3 |
| CPU | Apple M1 Max（10 核） |
| 内存 | 32 GB |
| Python | 3.9 |

---

## 2. 数据量

| 项 | 值 |
|----|-----|
| 股票数 | **1000**（编号 `000000` … `000999`） |
| 时间范围 | `20230101` … `20260101`（约 3 年） |
| 交易日 | **784** 天（周末休市） |
| K 线 | 日线，不复权 |
| 总行数 | `1000 × 784 = 784,000` |
| ST | 不写 |
| 怎么入库 | 直接写入临时库（不经中间 CSV） |
| 库文件位置 | `__performance__/.db/` |

规模改动看：`scripts/cmd/config.py`。

---

## 3. 策略怎么跑

| | entity | slice |
|--|--------|-------|
| 命令 | `devcli.py bpe` | `devcli.py bps` |
| 策略目录 | `test_strategies/entity_based/` | `test_strategies/slice_based/` |
| 运行模式 | 按股票分包（entity） | 按时间切片（slice） |
| 策略行为 | 空策略：不选股、不产生交易机会 | 同左 |
| 怎么调度 | 多进程，股票分包一起算 | 按时间切片；算的时候一般单进程，读可以多进程帮忙 |
| 数据库 | **仅 DuckDB**（默认） | 同左 |

两套策略固定不变，用来测引擎快慢，不测选股好不好。  
entity 和 slice **分开看，不要直接比谁更快**。

---

## 4. 报告产出什么

| 产出 | 说明 |
|------|------|
| 摘要位置 | `results/_local/entity_based/`、`results/_local/slice_based/` |
| 文件 | `REPORT.md`、`metrics.json` |
| 必写 | 数据库类型、运行模式、总执行时间、股票数/交易日、是否成功 |
| slice 另写 | 切了几片、读数据进程数、预读排队等 |
| 更细的时间拆分 | 策略结果目录里的 `performance.json`（系统自动生成） |

以套件里的 `REPORT.md` 为准核对总执行时间和数据库类型。字段约定见 [`REPORT_TEMPLATE.md`](./REPORT_TEMPLATE.md)。

---

## 附录

### A. 我们故意没做的事

也可以按「不同系统 × 不同数据库 × 不同数据量」做一大表。本轮 **只固定：macOS + 报告写明的数据库（默认 DuckDB）+ 上面的数据量**。换了数据库，报告里改数据库类型，不要和 DuckDB 的结果混在一张对比表里。

### B. 怎么再跑一遍

```bash
python devcli.py bpe              # entity，默认 / 仅 duckdb
python devcli.py bps              # slice，默认 / 仅 duckdb
python devcli.py bpe --db duckdb  # 显式写明（与默认相同）
python devcli.py bpc              # 清理临时库和本地结果
# python devcli.py bpe --db mysql   # 尚未实现，会退出
# python devcli.py bps --db pgsql   # 尚未实现，会退出
```

### C. 读结果时注意

- 按时间切片：读数据可以几个人帮忙，按日历往前算通常仍是一个人。  
- 测试数据是「每天每只股票都有行情」的假数据，比真实市场更「满」，会偏重一些。  
- MySQL / PgSQL：命令行有 `--db` 入口，**建库与注入尚未实现**，不要写进正式对比。
