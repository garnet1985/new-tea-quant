# Job Pipeline（`infra.job_pipeline`）

**模块：** `infra.job_pipeline` · **版本：** `0.1.0`

**最低支持核心版本：** `>=0.6.0`

长任务执行管道：统一任务登记表、串行排队与任务级进度摘要，作为前端可见的「管道」真相源。负责互斥与队列；细进度继续用 `infra.progress`。

## 适用场景

- 用户提交回测 / Tag / 数据更新等长任务：空闲则跑，忙则入队（有上限）
- UI 全局管道列表与「完成后提示 + 跳转」（只读任务表）
- 跨 tab / 回页时发现仍在跑或已结束的任务

## 模块依赖

- `infra.project_context`：定位 runtime 落盘目录
- `infra.progress`：把细进度摘要挂到任务快照；业务页仍可直接读 Progress

## 设计初衷

- **要解决的问题：** 互斥与进度分裂、忙则硬拒、前端无法稳定发现长任务状态。
- **明确不做（第一期）：** 条件并行、依赖图调度、分布式队列。

## 相关文档

- [设计与决策](./docs/DECISIONS.md)
- [架构](./docs/ARCHITECTURE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [快速开始](./QUICKSTART.md)
- [用户指南](./docs/USER_GUIDE.md)
- [测试用例](./__test__/TEST_CASES.md)
