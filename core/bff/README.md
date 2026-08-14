# BFF

`core/bff` 是顶层特殊模块（非 `core/modules` 形态）：FED 的 Flask BFF——HTTP 编排与 UI DTO，调用 `core.modules` / `core.infra`。
**无**对外 Python Facade / `contracts` / 根目录 `API.md`；元数据见 [`module_info.yaml`](module_info.yaml)。

HTTP 路径与响应契约优先以 FED 各页 `API.md` 为准（策略域暂无 FED `API.md`，见 [`docs/routes/strategy.md`](docs/routes/strategy.md)）。本模块文档只保留架构与编排索引。

## 适用场景

- 浏览器经 `/api` 访问策略 / 标签 / 数据源 / 安装与设置
- 生产模式由本进程托管 FED `build` 静态资源

## 启动

仓库根目录：`python -m core.bff.app`（配置见 `conf.py`：`HOST` / `PORT` / `DEBUG` / `CORS_*`）。

## 相关文档

- [架构与分层](docs/ARCHITECTURE.md)
- [业务域分组](docs/GROUPING.md)
- [路由编排索引](docs/ORCHESTRATION.md)
- [各域路由](docs/routes/)
