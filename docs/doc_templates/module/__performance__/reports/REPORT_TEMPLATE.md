# Performance Report — `{case_name}`

> 模块正式 bench 报告模板。复制到 `__performance__/results/<version>/<case>/REPORT.md` 后填写。  
> 模板版本：`v0.4-draft`

---

## Case

| 项 | 内容 |
|----|------|
| **名字** | `{case_name}` |
| **日期** | `{run_date}` |
| **模块 / 版本** | `{module}` `{version}` |

## 描述

`{一两句：测什么、为何测。例如：entity_based 空转，量框架调度开销。}`

## 测试环境

| 项 | 内容 |
|----|------|
| CPU | `{cpu}` |
| 内存 | `{memory}` |
| 存储 | `{storage}` |
| 数据来源 | `{data_source}` <!-- 本地 DB / 远程 DB / 文件 fixture 等 --> |
| 数据格式 | `{data_format}` <!-- 如 MySQL 表、CSV fixture --> |
| 操作系统 | `{os}` |
| 语言版本 | `{language}` <!-- 如 Python 3.x --> |
| 并发配置 | `{concurrency}` <!-- workers / epj 等，一行即可 --> |
| Cache | `{cache_state}` <!-- cold / warm；标准回归默认 cold --> |

## 测试输入数据

| 项 | 内容 |
|----|------|
| 说明 | `{input_desc}` |
| 路径 | `{input_path}` |
| 规模 | `{scale}` <!-- 如：N 只股票 × 日期区间 / K 线条数 --> |
| 模式 | `{execution_mode}` <!-- entity_based / slice_based / … --> |

## 测试脚本

```bash
{how_to_run}
```

脚本路径：`{script_path}`

## 结论

| 项 | 数值 | 备注 |
|----|------|------|
| **耗时** | `{wall_time}` | |
| **吞吐量** | `{throughput}` | 单位写清楚，如 K-lines/s |
| **并发度** | `{parallelism}` | 实测：`sum_worker_time / wall_time`；单进程可写 ~1× 或 — |
| **主要耗时点** | `{hotspot}` | 如：IO / 调度 / 业务计算 |
| **内存峰值** | `{peak_memory}` | 可选；无明显压力可写 — |

相对本 case 上次记录（可选；无记录则写「首次」）：

| 项 | 本次 | 上次 | 备注 |
|----|------|------|------|
| 耗时 | `{wall_time}` | `{wall_time_prev}` | |
| 吞吐量 | `{throughput}` | `{throughput_prev}` | |
| 并发度 | `{parallelism}` | `{parallelism_prev}` | |

补充（可选，一两句）：

`{notes}`

## 与业界产品对比

参照 [`devtools/performance/BENCHMARKS.md`](../../../devtools/performance/BENCHMARKS.md) 中有记录的数据；条件差很多时注明，勿强行对齐。

| 产品 | 吞吐量 | 相对本 case | 备注 |
|------|--------|-------------|------|
| **NTQ（本 case）** | `{throughput}` | 1.0× | |
| `{peer_1}` | `{peer_1_tp}` | `{peer_1_rel}` | `{peer_1_note}` |
| `{peer_2}` | `{peer_2_tp}` | `{peer_2_rel}` | `{peer_2_note}` |
