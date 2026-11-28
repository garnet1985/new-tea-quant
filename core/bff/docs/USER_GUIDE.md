# BFF 使用指南

**模块：** `bff` · **版本：** `0.2.2`

**最低支持核心版本：** `>=0.5.0`

## 能做什么

浏览器里的 FED 经本进程的 `/api` 访问策略、标签、数据源、安装向导、应用设置、AI 通道与 Agent。生产模式下同一进程还可托管 `core/ui/fed/build` 静态资源。

## 怎么启动

仓库根目录执行 `python -m core.bff.app`。监听地址与端口见 `core/bff/conf.py`（环境变量 `NTQ_BFF_HOST` / `NTQ_BFF_PORT`）。开发时 FED 通常走 `npm start`（另一端口），依赖 BFF 的 CORS 白名单。

## 怎么配

| 项 | 说明 |
|----|------|
| `NTQ_BFF_PORT` / `NTQ_BFF_HOST` | 监听 |
| `BFF_THREADED` | 设为 `0` 可关多线程 |
| FED build | 需先 `npm run build`（`core/ui/fed`）或由 dev CLI 挂载；未就绪时 `/` 返回 JSON 提示 |

HTTP 路径分组见 [`GROUPING.md`](GROUPING.md)；单路由契约优先看 FED 各页 `API.md` 与 [`routes/`](routes/)。

## 常见坑

- **不要把 BFF 当 Python 库 import**：领域逻辑在 `core.modules` / `core.infra` Facade。
- **CORS**：仅允许 `conf.py` 里列出的 dev/BFF 源；换端口要同步改配置。
- **安装向导子进程**：`db_connection` / `import_data` 会独占 DuckDB；BFF 会在拉起子进程前释放本进程持有的连接。
- **进度轮询**：策略工作台用 `GET …/run/progress`（V2-06b），不要用已移除的逐步 `…/<step>/progress`。
- **force_refresh**：POST run 体只认 `force_refresh`，不再接受旧字段 `is_force`。

## 相关文档

- [`../README.md`](../README.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`ORCHESTRATION.md`](ORCHESTRATION.md)