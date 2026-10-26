# Trace（`infra.trace`）

**模块：** `infra.trace` · **版本：** `0.1.2`

匿名 usage 上报。**默认关闭**（opt-in），需用户显式授权。对外门面为静态类 `Trace`。提供去敏感化、队列、发送、后台 drain 等能力。**不**经本模块处理应用内软反馈（属 `modules.ntq_external/feedback`）。

## 适用场景

- 安装完成、CLI 命令、分析动作等关键事件，静默且去敏感地上报，帮助维护者了解使用情况
- BFF / UI 长进程启动 `start_background_drain()` 后台发送队列

## 模块依赖

- `infra.machine_capacity`：机器能力探测模块：获取当前用户机器的能力信息的模块，用于给大性能需求的任务提供规划信息。
- `infra.project_context`：项目上下文模块：提供常用路径，配置，缓存，项目上下文信息的模块。
## 设计初衷

- **要解决的问题：** 把上报做成"用户同意才动、不同意向不留下任何痕迹"的独立模块，避免上报代码散落在各处。
- **明确不做：** 不做强制上报；不做应用内反馈（评分 + 文字反馈走 `modules.ntq_external`）。

## 常见问题

**Q：怎么改上报地址？**
A：`core/defaults.py`、环境变量 `NTQ_TRACE_ENDPOINT` 或 `userspace/system/config/trace.json`。详见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

## 相关文档

- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
