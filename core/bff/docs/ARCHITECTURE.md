# BFF 架构

**版本：** 0.2.0

`core/bff`：FED 的 Flask HTTP 编排层。领域执行在 `core.modules` / `core.infra`；本模块不做对外 Python Facade / contracts。

## 职责与边界

| 负责 | 不负责 |
|------|--------|
| HTTP 解析、入参校验、`ok`/`error` 信封 | 领域进度算法、业务落盘细节 |
| UI 列表 / snapshot 等 DTO（`helpers/`） | 引擎调度与加权进度 |
| 异步 submit 薄壳（锁、lease、线程） | Flask 之外的公开 Python API |
| CORS / 静态托管 FED `build` | userspace 策略/tag 业务逻辑 |

## 模块结构

```text
core/bff/
  module_info.yaml
  README.md
  app.py                 # 按域注册 blueprint（url_prefix=/api）
  conf.py
  static_ui.py           # 生产模式挂载 core/ui/fed/build
  shared/                # response / request / file_ops（无业务域知识）
  APIs/
    platform/            # health, runtime, setup, app_settings
    data/                # sources, contracts
    strategy/            # routes/ + helpers/
    tag/                 # routes/ + helpers/
  docs/
```

## 分层

| 层 | 允许 | 禁止 |
|----|------|------|
| `APIs/*/routes.py` 或 `routes/` | 解析 HTTP、校验入参、调 `implementer`、`ok`/`error` | 文件 I/O、DB、线程、DTO 拼装 |
| `APIs/*/implementer.py` 或 `routes/*/implementer.py` | 懒加载 import，编排 BFF helpers / core services | Flask 响应细节 |
| `APIs/*/helpers/` | UI 列表 / snapshot hydrate 等 DTO | 重领域写、引擎调度 |
| BFF `*_run.py` 薄壳 | 线程、进程内锁、lease、触发 core | 加权进度算法、业务落盘细节 |
| `modules/*/core/services` | 进度落盘、facade 执行 | Flask、HTTP 状态码 |
| `modules/*` facade | `Strategy.simulate` / `Tag.execute` 等领域 API | 页面字段命名 |
| `bff/shared/` | response envelope、pagination、file multipart | 任何业务域知识 |
| `bff/support/` | **废弃** 勿新增 | — |

## 归属裁决

1. 仅 UI 列表 / 多 version snapshot 读模型？→ BFF `helpers/`
2. 进度落盘 / 指纹缓存 / 引擎执行？→ 对应 `modules/*/core`
3. 多模块共用基础设施？（lease、cache cleanup、export）→ `core/infra`
4. 仅 HTTP/信封/CORS/静态资源？→ `core/bff`
5. 首次安装向导状态机？→ `bff/APIs/platform/setup`（依赖仓库根 `setup/`）
6. 名字含 settings？→ app 配置归 **platform/app_settings**；仿真 option catalog 归 **strategy**

## 依赖

见 [`../module_info.yaml`](../module_info.yaml)。

## 相关文档

- [`../README.md`](../README.md)
- [`GROUPING.md`](GROUPING.md) — 业务域与 URL
- [`ORCHESTRATION.md`](ORCHESTRATION.md) — 路由编排索引
- [`routes/`](routes/) — 各域路由细节
