# BE 性能测试前提

本轮在 **macOS** 上跑。默认 **DuckDB**；也可用 `--db mysql` / `--db pgsql`（读 userspace 里的连接配置）。  
报告里必须写明这次用的数据库类型。

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
| 最大股票数 | **1000**（`config.DEFAULT_STOCK_COUNT`；编号 `000000` …） |
| 自动分档 | **25% / 50% / 100%** → N250 / N500 / N1000（同库截取前 N 只，不反复 seed） |
| 时间范围 | `20230101` … `20260101`（约 3 年） |
| 交易日 | **784** 天（周末休市） |
| K 线 | 日线，不复权 |
| 满档总行数 | `1000 × 784 = 784,000` |
| ST | 不写 |
| 怎么入库 | 直接写入临时库（不经中间 CSV） |
| DuckDB 库文件 | `__performance__/.db/` |
| MySQL / PostgreSQL 库名 | 仅 `perf_test_tmp` / `perf_test_tmp_N`（不写业务库） |

规模改动看：`scripts/cmd/config.py`（改最大股票数与 `SCALE_FRACTIONS`）。

报告路径：`reports/{BE版本}/{mode}/N{股票数}/{duckdb|mysql|pgsql}/`；  
模式总览：`reports/{BE版本}/{mode}/OVERALL.md`（T0/k、翻倍吞吐变化、固定成本占比）。

---

## 3. 策略怎么跑

| | entity | slice |
|--|--------|-------|
| 命令 | `devcli.py bpe` | `devcli.py bps` |
| 策略目录 | `test_strategies/entity_based/` | `test_strategies/slice_based/` |
| 运行模式 | 按股票分包（entity） | 按时间切片（slice） |
| 策略行为 | 空策略：不选股、不产生交易机会 | 同左 |
| 怎么调度 | 多进程，股票分包一起算 | 按时间切片；算的时候一般单进程，读可以多进程帮忙 |
| 数据库 | 默认 DuckDB；可 `--db mysql` / `--db pgsql` | 同左 |

两套策略固定不变，用来测引擎快慢，不测选股好不好。  
entity 和 slice **分开看，不要直接比谁更快**。

### MySQL / PostgreSQL 注意

- 连接信息来自 `userspace/system/config/database/mysql.json` 或 `postgresql.json`（也可设 `DB_MYSQL_*` / `DB_POSTGRESQL_*`）。
- **没有配置**：直接退出，提示「不知道连接信息」。
- **有配置但连不上**：直接退出，提示「库没开或配置不对」。
- **能连上**：自动创建专用测试库 `perf_test_tmp*`，注入假数据后跑测。
- password 允许为空（本地常见）；仅拒绝占位符 `your_password_here`。
- **绝不**写入配置里的业务库名；若同名库已存在且不在本套件登记里，会中止以免误伤。

---

## 4. 报告产出什么

| 产出 | 说明 |
|------|------|
| 摘要位置 | `reports/{BE版本}/{模式}/N{股票数}/{duckdb\|mysql\|pgsql}/`，例如 `reports/0.4.0/entity_based/N1000/pgsql/`；总览见同模式 `OVERALL.md` |
| 文件 | `REPORT.md`、`metrics.json`（留档；`bpc` 默认不删版本目录） |
| 必写 | 跑测时间、BE/core/相关模块版本、数据库类型、总执行时间、是否成功 |
| 命令行 | 跑完打印简要摘要（版本 / 模式 / 库 / 总时间 / 速度 / 报告路径） |
| slice 另写 | 切了几片、读数据进程数、预读排队等 |
| 更细的时间拆分 | 四大步 + 少量小项；策略结果目录里还有完整 `performance.json` |

以套件里的 `REPORT.md` 为准核对总执行时间和数据库类型。字段约定见 [`REPORT_TEMPLATE.md`](./REPORT_TEMPLATE.md)。

---

## 附录

### A. 我们故意没做的事

也可以按「不同系统 × 不同数据库 × 不同数据量」做一大表。本轮固定机器与数据量；换了数据库，报告里改数据库类型，不要和 DuckDB 的结果混在一张对比表里。

### B. 怎么再跑一遍

```bash
python devcli.py bpe                 # entity，默认 duckdb
python devcli.py bps                 # slice，默认 duckdb
python devcli.py bpe --db mysql      # entity + MySQL
python devcli.py bps --db pgsql      # slice + PostgreSQL（也可用 --db postgresql）
python devcli.py bpc                 # 清理临时库（含 mysql/pgsql 测试库）和本地结果
```

### C. 读结果时注意

- 按时间切片：读数据可以几个人帮忙，按日历往前算通常仍是一个人。  
- 测试数据是「每天每只股票都有行情」的假数据，比真实市场更「满」，会偏重一些。  
- 换了数据库，报告里写清数据库类型，不要和 DuckDB 结果混在一张对比表里。
