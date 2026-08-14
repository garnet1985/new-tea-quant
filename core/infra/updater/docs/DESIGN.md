# Updater 详细设计

**版本：** `0.1.0`

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 模块边界 | 升级域（编排源码 + 扩展点）；安装归 infra.setup | 两模块零逻辑交叉 |
| 运行时位置 | `userspace/system/updater` 拷贝 | core 在 managed_scope 内会被覆盖 |
| 入口 | `Updater` Facade：data_scripts / post_upgrade / runtime | 对齐 CORE_MODULE_STANDARDS |
| 不提供 | `Updater.upgrade.run()` | 不能从当前 core import 跑镜像中的流水线 |
| CLI | `-m core.infra.updater.core.post_upgrade` | 镜像后子进程入口 |
| 空注册表 | post-upgrade 跳过不报错 | 测试可 clear；生产有内置 sync |
| 公开稳定性 | 最高 `beta` | core `0.x` |

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
