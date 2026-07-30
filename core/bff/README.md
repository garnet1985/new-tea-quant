# BFF API

`core/bff` 是 FED 的 Python BFF 层（Flask）：HTTP 编排 + 调用 `core.modules` / `core.infra` API。
页面读模型与异步 job 外壳落在各业务模块的 `launcher/`；BFF 不做领域逻辑。
`support/` 仅保留废弃占位，勿再写入。

## 启动

在仓库根目录执行：

```bash
python -m core.bff.app
```

默认配置读取：

- `core/bff/conf.py`
  - `HOST`
  - `PORT`
  - `DEBUG`
  - `CORS_*`

## 目录

```text
core/bff/
  app.py                 # 按域注册 blueprint
  shared/                # response / request / file_ops（无业务域知识）
  APIs/
    platform/            # health, runtime, setup, app_settings
    data/                # sources, contracts
    strategy/            # routes/ + helpers/
    tag/
  support/               # 废弃占位，勿再写入
```

域对照表见 [`GROUPING.md`](GROUPING.md)。编排索引见 [`ORCHESTRATION.md`](ORCHESTRATION.md)。

## 分层准则

| 层 | 允许 | 禁止 |
|----|------|------|
| `APIs/*/routes.py` 或 `routes/` | 解析 HTTP、校验入参、调 `implementer` / stack、`ok`/`error` | 文件 I/O、DB、线程、DTO 拼装 |
| `APIs/*/routes/*/implementer.py` 或 `stack.py` | 懒加载 import，编排领域 / launcher 调用 | Flask 响应细节 |
| `APIs/*/helpers/` | HTTP/DTO 辅助（以类方法组织） | 重业务编排、DB 写 |

| `modules/*/launcher/` | UI 读模型、分页 catalog、异步 job 外壳 | Flask、HTTP 状态码 |
| `modules/*` facade | `Strategy.simulate` / `Tag.execute` 等领域 API | 页面字段命名 |
| `bff/shared/` | response envelope、pagination、file multipart | 任何业务域知识 |
| `bff/support/` | **过渡期** 仅存尚未下沉的适配 | 新增逻辑默认不准进 support |

## 归属裁决

1. 只服务某一个 core 业务模块？→ 该模块 `launcher/`
2. 多模块共用基础设施？（lease、cache cleanup、export）→ `core/infra`
3. 仅 HTTP/信封/CORS/静态资源？→ `core/bff`
4. 首次安装向导状态机？→ `bff/APIs/platform/setup`（依赖仓库根 `setup/`）
5. 名字含 settings？→ app 配置归 **platform/app_settings**；仿真 option catalog 归 **strategy**

## 业务域

| 域 | 含 | 不含 |
|----|----|------|
| **strategy** | workbench + scan + package + strategy catalog | app 级 settings |
| **tag** | tag list + tag run | runtime/pipeline（平台能力） |
| **data** | data_source + data_contract 目录/新鲜度 | — |
| **platform** | health + runtime/pipeline + setup + app settings/cache | strategy 仿真 options |

## 说明

- 应用入口与注册：`core/bff/app.py`
- 生产模式托管 FED build：`static_ui.py` → `core/ui/fed/build`
- **HTTP 路径与响应契约保持不变**（重组不改 FED 契约）
