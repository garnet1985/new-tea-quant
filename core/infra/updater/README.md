# Updater（`infra.updater`）

**模块：** `infra.updater` · **版本：** `0.1.0`

应用升级编排：源码、DB 数据迁移脚本注册表、post-upgrade 收尾，以及把编排同步进 `userspace/system/updater` 供运行时调用。对外门面为 `Updater`。

## 适用场景

- CLI `python cli.py u` 或 BFF 触发升级时，按编排依次执行源码替换与数据迁移
- 把升级编排从 core 同步到 userspace，让运行时直接执行而不 import core.infra.updater

## 模块依赖

- `infra.utils`：工具函数模块：提供一些通用的业务无关的工具函数。例如日期处理，类型转换，CSV/归档 IO，确定性随
## 设计初衷

- **要解决的问题：** 把"升级流程"从"安装流程"（Setup）里分离，允许在已装环境上原地升级。
- **明确不做：** 不检查远端是否有更新（那是 Pro/云端能力）；不做版本回滚。

## 常见问题

**Q：为什么运行时不直接 import 本模块？**
A：编排会被 `sync_orchestrator` 拷贝到 userspace，运行时只调拷贝，避免 core 被 BFF 动态加载后版本漂移。详见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

## 相关文档

- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
