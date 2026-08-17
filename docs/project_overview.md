# New Tea Quant — 项目概览

> **定位**：面向 A 股量化研究与回测的本地优先平台。数据落盘、策略可插拔、回测可复现；CLI / HTTP API / 工作台同一套 core。

**相关入口：** [仓库 README](../README.md) · [模块文档标准](./module-doc-standard.md) · [Docker](./docker.md) · [CI smoke](../ci/README.md)

---

## 1. 这是什么

**New Tea Quant（NTQ）** 在本地完成：

1. **行情与衍生数据**：拉取、校验、按合同表结构入库  
2. **标签与策略**：可插拔扩展，CLI / 工作台触发  
3. **回测**：统一时间轴与执行语义，结果可复现、可导出  

**不是**云 SaaS、不是券商交易终端；默认不连实盘下单。

---

## 2. 仓库地图（顶层）

```text
new-tea-quant/
├── cli.py / devcli.py / install.py / launcher.py
├── Dockerfile / docker-compose.yml / .dockerignore
├── ci/                     # CI 专用（如 smoke_fresh_install）；非产品 runtime
├── docs/                   # 仓库级文档（本目录）
├── core/
│   ├── infra/              # 基础设施（DB、CLI、TaskGuard、trace…）
│   ├── modules/            # 业务模块（数据、标签、策略、回测…）
│   ├── bff/                # Flask BFF（HTTP 编排；托管 FED build）
│   ├── ui/                 # 工作台前端（fed/：React）
│   ├── system.json         # 发行元数据 SSOT（SystemMeta 只读此文件）
│   └── default_config/     # 默认配置 JSON
├── userspace/              # 用户数据与配置（gitignore 大部）
│   ├── system/             # config / db / backup / updater 等
│   ├── strategies/         # 用户策略包
│   └── extensions/         # 用户扩展（tags / data_source / adapters…）
└── experiments/            # 实验与草稿（非产品路径）
```

**运行时（通常不入库）：** `userspace/.ntq/`（如 TaskGuard 租约、trace 等）。

---

## 3. 分层怎么理解

自上而下：

| 层 | 目录 | 职责 |
|----|------|------|
| 展示 | `core/ui/fed/` | 工作台 UI（React） |
| 接入 | `core/bff/`、`cli.py`、`launcher.py` | HTTP / CLI / 一键启动 |
| 业务模块 | `core/modules/` | 数据、标签、策略、回测、适配器… |
| 基础设施 | `core/infra/` | DB、CLI 框架、发现、TaskGuard、trace、updater… |
| 用户落盘 | `userspace/` | 配置、库文件、策略与扩展源码 |

**依赖方向（硬约束）：** 上层可依赖下层；**infra 不得依赖 modules**；modules 之间只经公开门面与 `module_info.yaml` 声明依赖。细则见根目录 [`CORE_MODULE_STANDARDS.md`](../CORE_MODULE_STANDARDS.md)。

`core/bff` / `core/ui` 是顶层特殊模块（非 `core/modules` 形态），经 Facade / HTTP 调用 modules 与 infra。

---

## 4. `core/infra`（基础设施）

| 包 | 一句话 |
|----|--------|
| [`cli`](../core/infra/cli/) | 用户 CLI（`cli.py`）与开发 CLI（`devcli.py`） |
| [`cmd_layout`](../core/infra/cmd_layout/) | 命令布局 / 帮助结构 |
| [`db`](../core/infra/db/) | 数据库连接与访问约定 |
| [`discovery`](../core/infra/discovery/) | 模块 / 命令发现 |
| [`export_import`](../core/infra/export_import/) | 导出导入 |
| [`machine_capacity`](../core/infra/machine_capacity/) | 机器能力探测（如并行度建议） |
| [`project_context`](../core/infra/project_context/) | 仓库根、userspace 路径等上下文 |
| [`setup`](../core/infra/setup/) | 安装 / 首次配置（`install.py`） |
| [`task_guard`](../core/infra/task_guard/) | 单活跃长任务租约（`TaskGuard` / `TaskLease`） |
| [`trace`](../core/infra/trace/) | 运行时 trace 上报客户端 |
| [`updater`](../core/infra/updater/) | 更新流程 |
| [`utils`](../core/infra/utils/) | 跨模块小工具 |

并发与 worker 池属于 **`modules.backtest_engine`** 的执行面，**不是**独立 `infra.worker` / `infra.logging` 包。

---

## 5. `core/modules`（业务模块）

| 模块 | 一句话 | 文档入口 |
|------|--------|----------|
| [`data_contract`](../core/modules/data_contract/) | 表结构 / 合同定义 | [README](../core/modules/data_contract/README.md) |
| [`data_manager`](../core/modules/data_manager/) | 读路径、样本股池（`sample_universe`）等 | [README](../core/modules/data_manager/README.md) |
| [`data_source`](../core/modules/data_source/) | 拉取与落库编排 | [README](../core/modules/data_source/README.md) |
| [`indicator`](../core/modules/indicator/) | 指标计算 | [README](../core/modules/indicator/README.md) |
| [`tag`](../core/modules/tag/) | 标签扫描与结果 | [README](../core/modules/tag/README.md) |
| [`strategy`](../core/modules/strategy/) | 策略发现与模拟（scan / enumerate / price_factor / portfolio） | [README](../core/modules/strategy/README.md) |
| [`analysis`](../core/modules/analysis/) | 回测后解释 inputs 与 outputs 的关系（骨架） | [README](../core/modules/analysis/README.md) |
| [`backtest_engine`](../core/modules/backtest_engine/) | 回测时间轴与执行引擎 | [README](../core/modules/backtest_engine/README.md) |
| [`market_profile`](../core/modules/market_profile/) | 市场画像相关 | [README](../core/modules/market_profile/README.md) |
| [`adapter`](../core/modules/adapter/) | `Strategy.scan` 机会列表的后处理回调（userspace adapters） | [README](../core/modules/adapter/README.md) |

策略扩展约定：`userspace/strategies/<name>/` + `StrategyHooks`；scan 后处理见 `userspace/extensions/adapters/`。细节以各模块 README 与 `docs/` 为准。

---

## 6. 典型数据流（简图）

两条线分开看：**行情怎么进库 / 怎么被用**，以及 **scan 结果怎么交给 adapter**。  
（`modules.adapter` **不是**行情入口；它是 scan 产出的 callbacks。）

**① 数据路径（落库 → 读取 → 计算）**

```text
外部行情 Provider（handler 配置驱动）
        │
        ▼
  DataSource（拉取、校验、按合同写入）
        │
        ▼
  userspace DB（合同表）
        │
        ▼
  DataManager（统一读路径）
        │
        ├──► Indicator / Tag
        └──► Strategy + BacktestEngine（simulate / 回测等）
                    │
                    ▼
              结果落盘 / 导出
```

**② Scan → Adapter（机会后处理）**

```text
Strategy.scan（Scanner）
        │
        ▼
  Opportunity 列表 + context
        │
        ▼
  Adapter（按 scanner.adapters 依次 process）
        │
        ▼
  console / webhook / 自定义 userspace adapter …
```

**③ 入口（同一套 Facade）**

```text
CLI / BFF（工作台） / launcher
        │
        ▼
  modules.* 门面（DataSource、DataManager、Tag、Strategy、Adapter…）
```

长任务（数据续期、标签跑批、策略跑批等）经 **`TaskGuard`** 互斥；HTTP 对外状态路径仍为 `GET /api/v1/runtime/pipeline`（实现已切到 TaskGuard，见 `task_guard` 文档）。

---

## 7. 本地怎么跑（入口）

以仓库根目录 [`README.md`](../README.md) 的安装与命令为准。常见入口：

| 入口 | 用途 |
|------|------|
| `python install.py` | 安装 / 初始化 |
| `python cli.py` | 用户 CLI |
| `python launcher.py` | UI 安装引导 / 启动 |
| `python -m core.bff.app` | 单独起 BFF（可托管 FED build） |
| `python devcli.py` | 维护者工具（pack / 检查等） |
| `ci/smoke_fresh_install.py` | **仅 CI** 新鲜安装冒烟（勿当日常开发工具） |

Docker 说明见 [`docker.md`](./docker.md)。

---

## 8. 文档怎么找

| 想了解… | 去哪 |
|---------|------|
| 仓库级约定 / 模块文档规范 | [`docs/README.md`](./README.md)、[`module-doc-standard.md`](./module-doc-standard.md) |
| 某个模块 API / 架构 | 该模块根下 `README.md`、`API.md`、`docs/` |
| 新建模块骨架 | [`docs/doc_templates/`](./doc_templates/) |
| 模块边界硬约束 | [`CORE_MODULE_STANDARDS.md`](../CORE_MODULE_STANDARDS.md) |
| userspace 用户指南 | [`strategies`](../userspace/strategies/USER_GUIDE.md)、[`extensions/tags`](../userspace/extensions/tags/USER_GUIDE.md)、[`extensions/data_source`](../userspace/extensions/data_source/USER_GUIDE.md) |

本文件只做**地图**；表结构、命令细节、设计取舍以各模块文档与代码为准。
