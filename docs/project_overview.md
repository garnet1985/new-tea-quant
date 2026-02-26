# 系统架构概览

## 我们在解决什么问题？

New Tea Quant 是一个**面向研究和回测的量化框架**，希望帮用户把下面几件事拆清楚、做好用：

- **拿数据**：标准化地从各种数据源拉取并存好。
- **算东西**：技术指标、标签、策略信号等批量计算。
- **做实验**：从机会枚举，到价格层验证，再到带资金约束的回测。
- **管理工程复杂度**：路径、配置、并发、数据库、版本管理都由框架兜底。

整体设计遵循三条主线：

- **框架与用户空间分离**：`core/` 是框架核心，`userspace/` 是用户代码和配置。
- **Infra 打地基，Core Modules 做业务能力**：Infra 负责「项目 & 运行环境」，Core Modules 负责「量化业务能力」。
- **配置驱动 + 插件化**：通过配置文件与目录约定扩展，而不是到处写硬编码。

---

## 项目的亮点

- **完整的框架结构**
  - 从数据接入到数据库管理，从策略模拟到策略发现。
  - 覆盖了做系统性量化研究所需的完整基建。

- **配置驱动，低代码，低技术门槛**
  - 核心模块全部采用配置驱动，绝大部分调整都只需要修改配置而非修改代码。

- **更现代化的工程架构**
  - 高度模块化集成，高可扩展性。
  - 内核与用户空间分离，升级时保留 `userspace/`，其他用新版本覆盖即可。

- **枚举器 + 双模拟器的分层回测模式**
  - 把传统 on-bar 回测拆成「机会枚举 → 价格验证 → 资金回测」三步。
  - 机会枚举器产出标准格式的 SOT 数据，既是回测缓存层，又天然对机器学习与分析友好。

- **标签资产层**
  - Tag 系统可以对任何通用数据进行标签化，一个数据可以多场景，每个场景可以多标签，每个标签可以带自己的信息。
  - 标签既是「一次计算、多次复用、可追溯、跨策略」的资产层，也可视作加速回测的缓存层。

- **弹性多线程 / 多进程执行**
  - 在计算量大或 I/O 重的任务中，默认使用多线程或多进程，充分利用机器性能。
  - 队列大小可以自动调节，紧密控制内存使用，避免数据量大时内存溢出。
  - 搭配监控能力，可以对异常情况进行预警。

---

## 这个项目能提供什么？

面向「想做系统性量化研究和回测」的用户，New Tea Quant 提供的是一套**工程化的基础设施 + 业务框架**：

- **项目与配置管理**
  - 统一的路径管理（项目根、数据、日志、结果、配置等）。
  - `core/default_config` + `userspace/config` + 环境变量 的组合配置机制。
  - 针对不同环境（本地 / 服务器 / 生产）的可迁移项目结构。

- **数据获取与存储**
  - 基于配置的 DataSource 扩展点，方便对接多种外部数据源。
  - 统一的 schema 约定和数据库访问层（DataManager + DB infra）。

- **批量计算与资产沉淀**
  - 指标计算代理（Indicator）和标签资产层（Tag）。
  - 一次计算、多次复用、可追溯的标签和指标结果，支持多策略共享和后续分析 / ML。

- **策略研发与回测框架**
  - 从机会枚举（枚举器 SOT）到价格回测，再到带资金约束的回测的完整链路。
  - 多进程 / 多线程 / Orchestrator 支持高性能运行。
  - 版本管理与结构化结果输出，方便对比不同实验。

- **实时策略的扫描工具**
  - 当你已经有固定好的策略需要用于实战时，可以基于数据库最新数据进行全市场扫描。
  - 策略扫描器对全股票进行全策略扫描并生成机会对象。
  - Adapter 分发器为用户提供了对扫描出的机会进行下一步操作的入口（你可以接入第三方或自己定义的程序进行通知、机器学习、产生交易信号等）。

简而言之：**你专注于「策略逻辑、研究思路」，项目帮你兜住「工程地基」，同时也为你把策略用起来铺好了必要的底座**。

## 这个项目不打算做什么？

为了让边界清晰，有一些东西是刻意不做、或者只做很薄的一层：

- **框架不内置交易系统，如果需要得自行接入**
  - 不内置交易系统，但提供对最新数据的实时策略机会的扫描。

- **不做交易撮合 / 实盘执行引擎**
  - 本项目聚焦在研究与回测阶段，不直接对接券商或交易系统。
  - 如果需要实盘，可以在此之上绑定自己的交易执行层。

- **不做「一键自动赚钱」的黑盒策略**
  - 框架不内置黑盒策略，只提供构建和评估策略的能力。
  - 框架自带的交易策略是为了用户评估自己策略的一组bench mark

- **不做基础设施的巨人**
  - 倾向于只提供基础的底层数据核心，以后的扩展不会很大。
  - 不提供数据供应商，需要用户自己接入。默认的数据provider是免费或者无token的，需要用户自行购买

## 在路上的

- **更多可视化插件**
  - 回测结果现在已经默认支持策略结果的分析，但可视化还很薄弱，以后会陆续加强
  - 整个项目还没有上线UI（其实已经有了，还在测试试运行阶段，会在稳定版里推出）

- **更强大的机器学习能力**
  - 框架已经内置机器学习的能力，只是非常初级，之后的版本会不断加强

- **更通用的分析能力**
  - 框架将来会内置更多金融的默认统计和分布方法，帮助用户快速通过配置得到丰富的金融结果

---

## 顶层目录结构（project 视角）

```text
new-tea-quant/
├── core/                          # 框架核心（你尽量不要改）
│   ├── modules/                   # 核心业务模块
│   │   ├── strategy/              # 策略 & 回测框架（枚举器 + 双模拟器）
│   │   ├── data_manager/          # 数据管理器（读写数据库）
│   │   ├── data_source/           # 数据源系统（抓数据）
│   │   ├── tag/                   # 标签系统（一次算好，多次复用）
│   │   └── indicator/             # 技术指标（对 pandas-ta 的代理）
│   ├── infra/                     # 基础设施
│   │   ├── db/                    # 数据库连接 & Schema 管理
│   │   ├── worker/                # 多进程 / 多线程 / Orchestrator
│   │   ├── discovery/             # 自动发现模块和类
│   │   └── project_context/       # 路径、配置、文件、环境
│   └── default_config/            # 框架默认配置（不可变基线）
├── userspace/                     # 用户空间（你真正工作的地方）
│   ├── strategies/                # 用户策略
│   ├── data_source/               # 用户自定义数据源
│   ├── tags/                      # 用户标签场景
│   └── config/                    # 用户项目配置（覆盖 core/default_config）
└── docs/                          # 文档
    ├── architecture/              # 架构 & 设计文档（当前这个文件在这里）
    ├── getting-started/           # 安装、配置、上手
    └── development/               # 测试、覆盖率、Road-map
```

---

## 从「项目」视角看整体运行流程

### 1. 项目与环境：ProjectContext + DefaultConfig

- `core/infra/project_context/` 负责：
  - **PathManager**：统一管理所有路径（项目根目录、数据目录、日志目录、配置目录等）。
  - **ConfigManager**：把 `core/default_config/`、`userspace/config/` 和环境变量组合成一份最终配置。
  - **FileManager` 等**：对文件和目录的通用操作封装。
- `core/default_config/` + `userspace/config/` 共同定义：
  - 默认行为（框架给出的「推荐值」）。
  - 每个项目的差异化配置（只写差异，默认值自动补全）。

**效果**：项目级别的「路径、配置、环境」问题统一由一套机制解决，用户不需要到处硬编码路径，也不需要手写一堆 config 解析代码。

### 2. 数据层：DataSource + DataManager + DB

- `core/modules/data_source/`：
  - 根据配置（和 discovery）找到对应的 Handler / Provider。
  - 拉取原始数据、标准化、落地成统一 schema。
- `core/infra/db/`：
  - 提供数据库连接、连接池、迁移 / Schema 管理等能力。
- `core/modules/data_manager/`：
  - 在上面这些 infra 之上提供「领域化的数据访问 API」，比如：
    - 取 K 线、取复权数据、取财报数据、取交易日历等。

**效果**：数据获取与存储是一个完整闭环：**配置驱动的数据抓取 → 结构化入库 → 通过 DataManager 以领域 API 方式取出**。

### 3. 计算层一：Indicator + Tag（把「可复用资产」先算好）

- `core/modules/indicator/`：
  - 基于 `pandas-ta-classic` 做一层代理，统一指标调用方式。
  - 提供方便的高层 API，也暴露通用的低层接口。
- `core/modules/tag/`：
  - 把「一段逻辑在某个场景下的计算结果」当成**标签资产**，写入 JSON：
    - **一次计算，多次复用，可追溯，跨策略**。
  - 使用 `worker` infra 做多进程计算，支持增量更新与全量刷新。

**效果**：大量重复使用、计算代价高的东西（指标、标签）可以先算好、存好，再被策略和下游分析多次使用，而不是每次回测都现算一遍。

### 4. 计算层二：Strategy（从枚举，到价格验证，再到资金回测）

`core/modules/strategy/` 的核心是一个**四层架构**：

- **Layer 0：OpportunityEnumerator（底层枚举器 / SOT / 缓存层）**
  - 全市场、全周期地枚举所有潜在机会，生成 CSV 双表（opportunities + targets）。
  - 这是整个框架的**底层事实表**，同时也是「回测缓存层」：
    - 一次枚举，多次复用，方便分析软件和机器学习使用。
    - 可追溯：任何一条机会都能追到具体股票、具体日期、具体触发条件。
- **Layer 1：Scanner**
  - 针对最新一日做扫描，产出实时机会（active Opportunity），用于实盘提示。
- **Layer 2：PriceFactorSimulator（价格回测）**
  - 在不考虑资金约束的前提下，基于枚举器的 SOT 结果快速验证「价格层策略是否有 alpha」。
  - 速度非常快，适合频繁调参与因子实验。
- **Layer 3：CapitalAllocationSimulator（带资金的回测）**
  - 在价格层策略被证明有效后，进一步引入资金约束、多股票、费用等，模拟真实交易过程。
  - 仍然复用同一份 SOT 枚举结果，只是在其上叠加资金管理逻辑。

**效果**：策略研发被拆成多个清晰阶段：**机会枚举 → 价格验证 → 资金回测**，再配合 Worker 和版本管理，用户可以快速迭代策略而不被工程复杂度拖慢。

### 5. 并发与运行：Worker + Orchestrator

- `core/infra/worker/` 提供：
  - 传统的 `ProcessWorker` / `MultiThreadWorker`（多进程 / 多线程执行器）。
  - 模块化的 Orchestrator（Executor + JobSource + Monitor + Scheduler + Aggregator + ErrorHandler）。
  - 内存感知调度等高级特性。
- 上层模块（DataSource / Tag / Strategy）只需描述「有哪些 Job 要跑」，并选择合适的 Worker 组合，具体的并发执行和资源控制由 Worker 层负责。

**效果**：CPU 密集 / I/O 密集的任务都能以统一方式并发执行，而不用在每个模块里重复造轮子。

---


## 想看某个模块的细节？

本文件只是 project 级别的「总览图」，每个模块都有自己的三件套文档：`overview.md` / `architecture.md` / `decisions.md`。

- **核心业务模块（Core Modules）**
  - `core_modules/strategy/overview.md`
  - `core_modules/data_manager/overview.md`
  - `core_modules/data_source/overview.md`
  - `core_modules/tag/overview.md`
  - `core_modules/indicator/overview.md`
  - `core_modules/adapter/overview.md`

- **基础设施（Infra）+ 默认配置**
  - `infra/project_context/overview.md`
  - `infra/worker/overview.md`
  - `infra/db/overview.md`
  - `infra/discovery/overview.md`
  - `default_config/overview.md`

安装与上手，请参见：

- `../getting-started/installation.md`
- `../getting-started/configuration.md`
- `../getting-started/venv-usage.md`

开发与维护相关内容，请参见：

- `../development/testing.md`
- `../development/coverage.md`
- `../development/road-map.md`
