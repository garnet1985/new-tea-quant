# Tag Module — Boundary Notes

## 与 BacktestEngine

| 谁 | 干什么 |
|----|--------|
| **BE** | **仅 per_entity 时序**：jobs 调度、Timeline/Slice、JobContext.init |
| **Tag** | per_entity：JobBuilder + JobExecutor + flush；**global / non_ts：自备轻量主进程推进器**（不进 BE） |

## 包布局

```text
tag/
  tag.py              # Facade（对外；按 data.base 分发）
  contracts.py        # hooks / 公开类型
  api.yaml / glossary.yaml / module_info.yaml
  core/
    bff_support/      # UI：TagCatalog / TagRunLauncher
    engines/
      per_entity/     # BE：entity_based / slice_based + shared
      global_based/   # 轻量主进程（包名不可用 global 关键字）
      non_time_series/
    services/         # discovery / metadata_ensure / entity_list
    data_class/       # Scenario / TagDefinition
```

- CLI 在 **`core/infra/cli`**（`cli.py tag`），模块内不放 `__main__` / `run_tag`
- **禁止**再引入 BaseTagWorker / JobPipeline / 旧 timeline|sliced 编排
- global / non_ts：**不**把 `execution.mode` 映射到 BE，不设 mode 探针
- non_ts：主进程 **一次** `calculate_tag`；落库 `as_of` = 计算窗 `end_date`（无日历循环）
- incremental 水位：``sys_tag_calc_progress.last_calculated_end``（DB），**不是** max(as_of) / calculated_at / scenario.updated_at
- **表 SOT**：`attach_to_data_key` 仅在 ``sys_tag_scenario``；``sys_tag_value`` 只存点事实（as_of + json_value）；frontier 在 progress，value ≠ 水位
- per_entity 实体池：base 的 ``meta.list_data_key``
