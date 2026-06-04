# Price 调度规划

用户配置 **`entities_per_job`**（默认 1000）。

ProcessPool 并行度由 **`core/default_config/worker.json`** → **`job_pipeline`** 决定（非策略 settings）：

| Profile | 用途 |
| --- | --- |
| `default` | 兜底 |
| `enumerator` | 机会枚举 |
| `tag` | 标签 |
| `price_factor` | 价格因子 |
| `scanner` | 扫描器 |

各 profile 继承 `default`，可单独设 `reserve_cores` / `max_parallel_jobs_cap`（ProcessPool 同时 in-flight job 上限）。

用户可在 **`userspace/config/worker.json`** 用相同结构覆盖，例如：

```json
{
  "job_pipeline": {
    "price_factor": { "reserve_cores": 2 }
  }
}
```

策略 settings 里的 `max_workers` 会被忽略。
