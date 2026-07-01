# slice_based 枚举（Strategy 侧）

## 职责

| 层 | 负责 |
|----|------|
| **BacktestEngine.slice_based** | 探针、分片规划、并发、监控 |
| **Strategy（本目录）** | `execute_fn`：解析 job → 调 hooks → 输出 opportunities |

Strategy **不做** 探针、preload、reader/compute 进程编排。这些在 BacktestEngine。

## 文件（用户无关）

```
pipeline.py   → 组 job，交给 BacktestEngine.slice_based.run
worker.py     → execute_fn：build_payload + SliceBasedCompute.run
compute.py    → 按 open_dates 驱动 on_calendar_asof / scan_opportunity / holdings
resolver/     → 日历与 job 字段
state/        → 持仓状态
context/      → DataContext 组装
```

用户只写 `contracts` + hooks，不 import 本目录。

## session_state

一次 enumerate 内跨开市日状态，经 `ctx.calendar["session_state"]` ↔ `CalendarAsOfResult.session_state` 传递。
