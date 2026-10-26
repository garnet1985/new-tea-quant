# Progress（`infra.progress`）

**模块：** `infra.progress` · **版本：** `0.2.1`

## 简介

进度统一写进文件。一次任务一个 JSON 文件，按节点 id 一层层写进度；另可用 `Progress.channel` 写频道化 job 快照。前端 BFF、CLI、PHP 安装脚本都能读同一份进度，不用各自维护进度状态。短时间内多次 tick 会合并成一次写盘。

## 适用场景

- 长时间任务（扫描、回测、更新数据）需要告诉 UI 做到哪了
- 一个任务有多层步骤（比如先加载、再处理、最后保存），每层都有自己的进度

## 模块依赖

- `infra.project_context`：定位进度文件存储目录

## 设计初衷

- **要解决的问题：** 之前各模块各自写进度、界面要认多套字段。现在统一成进度文件，界面只读这一套。
- **明确不做：** 不存结果、机会列表、失败日志（业务结果由各模块自己保存）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [快速开始](./QUICKSTART.md)
- [决策](./docs/DECISIONS.md)
