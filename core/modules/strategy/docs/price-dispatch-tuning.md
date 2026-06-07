# Price 调度规划

ProcessPool 并行度与 batch 分组均由 **`core/default_config/worker.json`** → **`job_pipeline.price_factor`** 决定（非策略 settings）。

| 配置块 | 说明 |
| --- | --- |
| `reserve_cores` / `max_parallel_jobs_cap` | ProcessPool 并行 job 上限 |
| `dispatch.entities_per_job` | 每个 dispatch job 顺序处理的股数（默认 1000） |
| `dispatch.dispatch_probe` | `entities_per_job=auto` 时是否跑时间探针 |

用户可在 **`userspace/config/worker.json`** 用相同结构覆盖，例如：

```json
{
  "job_pipeline": {
    "price_factor": {
      "dispatch": { "entities_per_job": 500 }
    }
  }
}
```

策略 settings 里的 `entities_per_job`、`max_workers` 等会被忽略并告警。
