# System Actions 详细设计

**版本：** `0.2.0`

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅 `SystemActions` | 统一调用面 |
| 懒导入 | Facade 方法内 import | BFF 冷启动不拉 strategy/tag |
| 实现布局 | `core/cache_cleanup`、`core/shortcuts` | 与其它 infra 模块一致 |
| 租约文件 | `userspace/.ntq/runtime/pipeline_active.json` | 与进度文件同区 |
| 公开稳定性 | 最高 `beta` | core `0.x` |

## 行为要点

- `cache.run`：未选选项 → `nothing_selected`；busy → `pipeline_busy`
- `clear_strategy_results`：整棵 `results/`；与 `clear_backtest_results` + `clear_scan_results` 重叠（前者覆盖后者之和）
- `pipeline.lease`：`kind` 须在 `VALID_KINDS`；上下文退出时按 `job_id` 释放；辅助方法挂在 `PipelineLease` 类上
- `scaffold.*`：校验 machine-readable 路径；复制模板并将 `is_enabled=True`，注入 `meta.key`

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
