# Update 详细设计

**版本：** `0.5.0`

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 模块边界 | 仅注册表 + 收尾执行 | 与 `setup/updater` 编排分离 |
| 入口 | `Update` Facade | 对齐 CORE_MODULE_STANDARDS |
| CLI | 保留 `-m …post_upgrade` | updater 子进程已依赖 |
| 空注册表 | post-upgrade 跳过不报错 | 允许零动作升级 |
| 公开稳定性 | 最高 `beta` | core `0.x` |

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
