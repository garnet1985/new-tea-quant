# System Actions 详细设计

**版本：** `0.2.0`

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅 `SystemActions` | 统一调用面 |
| 懒导入 | Facade 方法内 import | BFF 冷启动不拉 strategy/tag |
| 实现布局 | `core/pipeline_lease`、`core/shortcuts` | 与其它 infra 模块一致 |
| 租约文件 | `userspace/.ntq/runtime/pipeline_active.json` | 与进度文件同区 |
| 公开稳定性 | 最高 `beta` | core `0.x` |
| 临时文件清理 | 不在本模块 | 属 devcli / 设置维护动作，见 `temp_cleanup` |

## 行为要点

- `pipeline.lease`：`kind` 须在 `VALID_KINDS`；上下文退出时按 `job_id` 释放；辅助方法挂在 `PipelineLease` 类上
- `scaffold.*`：校验 machine-readable 路径；复制模板并将 `is_enabled=True`，注入 `meta.key`

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
