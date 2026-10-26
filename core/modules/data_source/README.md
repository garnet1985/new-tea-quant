# Data Source（`modules.data_source`）

**模块：** `modules.data_source` · **版本：** `0.4.0`

## 简介

对接外部数据源（Tushare、Yahoo、自建 Provider 等），把数据拉下来存进本地数据库。支持按配置定时增量更新，新数据源加 Provider + Handler 就行，不用改主流程。

## 适用场景

- 首次运行 NTQ，需要拉全量的股票、指数、宏观数据
- 每天 / 每周自动增量更新最新行情
- 想接一个新数据源（比如 Wind、东方财富），不想改框架代码

## 模块依赖

- `infra.cmd_layout`：终端展示
- `infra.db`：底层数据库操作
- `infra.discovery`：自动发现外部 Provider
- `infra.project_context`：路径与配置
- `infra.utils`：通用工具
- `modules.data_manager`：数据落库后的读回与校验

## 设计初衷

- **要解决的问题：** 抓取是"和外部打交道"，取数是"本地读取"，两件事分开。抓取还需要速率限制、并发控制、重试等。
- **明确不做：** 不做本地数据读取（那是 `data_manager`）；不做声明式取数（那是 `data_contract`）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
