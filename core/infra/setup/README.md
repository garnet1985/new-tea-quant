# Setup（`infra.setup`）

**模块：** `infra.setup` · **版本：** `0.1.1`

安装编排、安装步骤、安装产物工厂。**不是** setuptools 的 `setup.py`。CLI / `install.py` / `launcher.py` / BFF 只调用门面 `Setup`。应用升级见 `infra.updater`。

## 适用场景

- 首次启动 NTQ 时，编排环境检测（依赖检查、目录创建、产物拷贝）
- 安装 CLI 运行时 / UI 运行时等可选组件

## 模块依赖

- `infra.cmd_layout`：命令行UI模块：给命令行工具提供一套通用的UI组件，方便其他模块展示结果。
- `infra.project_context`：项目上下文模块：提供常用路径，配置，缓存，项目上下文信息的模块。
- `infra.trace`：使用追踪模块：追踪一些重要事件的模块，用于改善用户体验，统计分析错误的模块。
- `infra.utils`：工具函数模块：提供一些通用的业务无关的工具函数。例如日期处理，类型转换，CSV/归档 IO，确定性随
## 设计初衷

- **要解决的问题：** 把"怎么装"与"装上了之后怎么跑"分开；安装流程可以在 CLI / BFF / 独立安装器三处复用同一份编排。
- **明确不做：** 不做升级（属 `infra.updater`）；不做业务配置迁移。

## 常见问题

**Q：安装产物 zip 在哪？**
A：`initialization/userspace/` 和 `initialization/data/`，方便用户手动取。

## 相关文档

- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
