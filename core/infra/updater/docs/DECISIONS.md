# infra.updater — 设计与决策

**模块：** `infra.updater` · **版本：** `0.1.1`

**最低支持核心版本：** `>=0.5.0`

本文记录 infra.updater 模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

负责**升级域**的编排（升级源码 + 扩展点），与安装域（`infra.setup`）零逻辑交叉。升级运行时须能在 core 被覆盖替换的过程中存活并继续执行；core `0.x` 阶段公开面稳定性不超过 `beta`。

## 方案与思路

- **模块边界：** 只做升级编排，安装归 `infra.setup`，两模块零逻辑交叉。
- **运行时位置：** 运行时从 `userspace/system/updater` 的拷贝执行——core 在 managed_scope 内会被覆盖。
- **入口：** `Updater` Facade 暴露 data_scripts / post_upgrade / runtime；不提供 `Updater.upgrade.run()`（不能从当前 core import 跑镜像中的流水线）。
- **CLI：** 镜像后子进程入口为 `-m core.infra.updater.core.post_upgrade`。
- **空注册表：** post-upgrade 跳过不报错（测试可 clear；生产有内置 sync）。

具体拍板见下文 DEC-01 / DEC-02。

---

## DEC-01：模块边界与 Facade 形态

| 决策 | 选择 | 理由 |
|------|------|------|
| 模块边界 | 升级域；安装归 infra.setup | 两模块零逻辑交叉 |
| 运行时位置 | `userspace/system/updater` 拷贝 | core 在 managed_scope 内会被覆盖 |
| 入口 | `Updater` Facade：data_scripts / post_upgrade / runtime | 对齐 CORE_MODULE_STANDARDS |
| 不提供 | `Updater.upgrade.run()` | 不能从当前 core import 跑镜像中的流水线 |
| CLI | `-m core.infra.updater.core.post_upgrade` | 镜像后子进程入口 |
| 空注册表 | post-upgrade 跳过不报错 | 测试可 clear；生产有内置 sync |
| 公开稳定性 | 最高 `beta` | core `0.x` |

## DEC-02：预生产形态与后续重做范围

**是什么：** 当前 updater 满足「同步编排到 userspace + 注册表扩展点 + post-upgrade 收尾」；**未**作为日常生产升级主路径全面收口。

**为什么这样：** core `0.x` 允许在不大改 Facade 契约的前提下重做 `core/orchestrator` 内部流水线（下载、镜像替换、migrate CLI 产品化等）。

**放弃了什么：** 本轮不做 migrate CLI 深度 redesign、不把 orchestrator 再拆成第二套公开 Facade。

**影响：** 文档与测试保持现有覆盖；新功能优先走 `data_scripts` / `post_upgrade` 注册表；orchestrator 内部大改须同步 userspace 拷贝与 DEC 追加。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)