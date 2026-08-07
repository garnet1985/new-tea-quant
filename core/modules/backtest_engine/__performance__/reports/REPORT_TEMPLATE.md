# 性能测试报告模版说明

机器可填充模版（`{{:token}}`，经 `Utils.markdown` 写出）：

| 文件 | 用途 |
|------|------|
| [`CASE_REPORT.md`](./CASE_REPORT.md) | 单档报告 → `reports/{BE}/{mode}/N{n}/{db}/REPORT.md` |
| [`OVERALL_TEMPLATE.md`](./OVERALL_TEMPLATE.md) | 模式总览 → `reports/{BE}/{mode}/OVERALL.md` |

变长块（调度小项、时间小项、分库表）在 Python 里先渲成字符串，再填进对应 token（如 `schedule_section` / `time_section` / `engines_detail_section`）。

每次 `bpe` / `bps` 按最大股票数自动跑多档（默认 25% / 50% / 100%），每档一份 `REPORT.md` + `metrics.json`，跑完写模式级 `OVERALL.md`：

```text
reports/
├── REPORT_TEMPLATE.md          # 本说明
├── CASE_REPORT.md              # 单档 fill 模版
├── OVERALL_TEMPLATE.md         # 总览 fill 模版
├── test_preconditions.md
└── {BE版本}/                   # 如 0.4.0
    ├── entity_based/
    │   ├── OVERALL.md
    │   ├── N500/{duckdb,mysql,pgsql}/
    │   ├── N1000/...
    │   └── N2000/...
    └── slice_based/
        └── （同上）
```

换了 BE 版本再跑，会进新目录，旧报告保留。  
同一次命令只测一个 `--db`；库之间不要混比。entity / slice 分看。

---

## 一、环境（跑在什么机器、什么库、什么版本）

| 报告里写什么 | 含义 | 例子 |
|--------------|------|------|
| 跑测时间 | 这次跑完写报告的时间（UTC） | 2026-08-06T07:24:57Z |
| 回测引擎 (BE) | 当前模块版本 | 0.4.0 |
| core | 核心版本 | 0.4.x |
| 相关模块 | 影响速度的依赖版本 | data_manager 0.4.0, strategy 0.7.0, … |
| 操作系统 / CPU / 内存 / Python | 机器环境 | macOS / M1 Max / 32 GB / 3.9 |
| 数据库类型 | duckdb / mysql / pgsql | pgsql |
| 数据库名称 | 这次用的临时库名 | perf_test_tmp |

**任何引擎或核心依赖变版本，速度都可能变**——报告必须写清版本，才能和历史档对比。

---

## 二、结果（跑得怎样）

### 大家都要写

| 报告里写什么 | 含义 |
|--------------|------|
| 运行模式 | 按股票分包（entity）或按时间切片（slice） |
| 样本档 | N500 / N1000 / …（相对最大股票数的比例） |
| 总执行时间（秒） | 从开始到结束，人真实等待的时间 |
| 股票数 / 交易日数 / 数据量（行） | 规模 |
| 处理速度 | 数据量 ÷ 总执行时间（股票×交易日 / 秒） |
| 是否成功 | 成功 / 失败 |

### 调度情况（按模式）

**entity**：同时开几个进程 / 任务包数量 / 每包多少只股票  

**slice**：计算/读数据进程数、预读排队、每片天数、片数、每只股票装载几次  

### 时间花在哪（四大步 + 少量小项）

空策略下「推进日历 / 引擎开销」≠ 选股算力。

1. 准备/规划 → 试跑采样 / 正式规划（entity）；调度采样说明（slice）  
2. 读数据 → 装合约或单片读数等  
3. 推进日历 / 引擎开销 → 上下文 / as-of / tick 或片内推进  
4. 写报告  

### 并行效果

并行效果 / 并行效率：多干活叠在一起的程度；slice 多反映「读是否帮上忙」。

---

## 三、单档 fill 模版长这样

见 [`CASE_REPORT.md`](./CASE_REPORT.md)（token 形如 `{{:wall_time}}`）。

总览见 [`OVERALL_TEMPLATE.md`](./OVERALL_TEMPLATE.md)。

`metrics.json` 与报告字段对齐，便于以后自动对比。
