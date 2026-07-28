# Tag Module — Boundary Notes

## 与 BacktestEngine

| 谁 | 干什么 |
|----|--------|
| **BE** | jobs 调度、Timeline、JobContext.init |
| **Tag** | JobBuilder 喂 jobs；JobExecutor 实现 RunCallbacks；Pipeline 编排 + flush |

## 包布局

```text
tag/
  tag.py              # Facade（对外）
  contracts.py        # hooks / 公开类型
  api.yaml / glossary.yaml / module_info.yaml
  core/
    bff_support/      # UI：TagCatalog / TagRunLauncher
    engines/          # entity_based / slice_based + shared
    services/         # discovery / metadata_ensure / entity_list
    data_class/       # Scenario / TagDefinition
```

- CLI 在 **`core/infra/cli`**（`cli.py tag`），模块内不放 `__main__` / `run_tag`
- **禁止**再引入 BaseTagWorker / JobPipeline / 旧 timeline|sliced 编排
- incremental 水位：``sys_tag_calc_progress.last_calculated_end``（DB），**不是** max(as_of) / calculated_at / scenario.updated_at
- **表 SOT**：`attach_to_data_key` 仅在 ``sys_tag_scenario``；``sys_tag_value`` 只存点事实（as_of + json_value）；frontier 在 progress，value ≠ 水位
