## 变更日志（Changelog）

本文件汇总 New Tea Quant 的主要版本变更。  
自 `v0.1.0` 起采用统一版本规范 `v[a].[b].[c]`（a=大版本，b=小版本，c=微小版本）。  
`v0.0.x` 段为对历史内部里程碑（原文档中的 v2/v3/v4）的回溯编号。

---

### Unreleased

- `modules.strategy`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、`docs/components/` 下各子组件说明、重写模块 `README.md`；删除模块根目录 `ARCHITECTURE.md` 与 `docs/core_modules/strategy/*`；`__init__.py` 指向 `README`/`docs`；修复 `components/scanner/scanner.py` 错误 import、Job使用完整 `settings` 与 `StrategyInfo` worker 元数据、`_scan_stocks` 内计时变量；`DataLoader` 改为纯 `List[Dict]` 行式处理（`load_rows_for_stock`），并删除 `core/data_class/` 目录；`docs/project_overview.md` 与 `docs/README.md` 导航更新。
- `modules.tag`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、重写模块 `README.md`；删除模块根目录 `ARCHITECTURE.md`、`DECISIONS.md` 与 `docs/core_modules/tag/*` 重复文档；`__init__.py` 模块说明指向 `README`/`docs`；`docs/project_overview.md` 与 `docs/README.md` 导航更新。
- `modules.data_cursor`：补齐 `module_info.yaml`、`__init__.py` 导出与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、模块 `README.md`；`data_cursor_manager.py` 补全 `Any` 类型导入；`docs/project_overview.md` 与 `docs/README.md` 导航更新。
- `modules.indicator`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、重写模块 `README.md`；删除 `docs/core_modules/indicator/*`；`docs/project_overview.md` 与 `docs/README.md` 导航更新；保留根目录 `AVAILABLE_INDICATORS.md`供策略配置引用。
- `modules.data_source`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、重写模块 `README.md`；删除原冗长 `README.md` 中失效外链与已不存在的 `SimpleConfigHandler` 描述；删除 `docs/core_modules/data_source/*`；`__init__.py` 增加模块文档指针；`docs/project_overview.md` 与 `docs/README.md` 导航更新。
- `modules.data_manager`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、重写模块 `README.md`；删除模块根目录 `API.md`、`ARCHITECTURE.md` 与 `docs/core_modules/data_manager/*` 重复文档；`__init__.py` 模块说明更新；`docs/project_overview.md` 与 `docs/README.md` 导航更新。
- `modules.data_contract`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS、CONCEPTS）、重写模块 `README.md`；删除模块根目录 `DESIGN.md`、`DECISIONS.md`、`CONCEPTS.md` 以免双源；`docs/project_overview.md` 与 `docs/README.md` 导航更新。
- `modules.adapter`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、模块 `README.md`；删除 `docs/core_modules/adapter/*` 重复文档；`docs/project_overview.md` 与 `docs/user-guide/examples.md` 导航指向模块内文档。
- `infra.logging`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、模块 `README.md`；`docs/project_overview.md` 导航指向模块内文档；`__init__.py` 导出 `LoggingManager`。
- `module_info.yaml` 字段简写：`name`、`version`、`description`、`dependencies`（不再使用 `module_` 前缀）；`docs/module-doc-standard.md` §4.6 已同步。
- 已迁移的 `infra/db`、`infra/discovery`：删除 `docs/infra/db/*`、`docs/infra/discovery/*` 重复文档；`docs/project_overview.md` 改为指向模块内文档。
- `infra.project_context`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、模块 `README.md`；删除 `docs/infra/project_context/*` 与根目录 `DESIGN.md`；`docs/default_config/*` 中链接改为指向 `core/infra/project_context/docs/`。
- `infra.worker`：补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS）、重写模块 `README.md`；删除 `docs/infra/worker/*` 与根目录 `DESIGN.md`；`docs/project_overview.md` 导航指向模块内文档。
- 文档治理约定落地：明确根目录 `README.md` 为主入口，统一命令入口为 `start-cli.py`。
- 明确发布时文档最低同步要求：至少更新 `README.md` 与 `CHANGELOG.md`。
- 记录 `docs/development/` 当前作为内部工作区文档，暂不纳入对外文档整理范围。
- 新增模块文档统一规范 `docs/module-doc-standard.md`，定义模块文档清单、固定模板和更新触发规则。
- 明确文档目录采用混合方案：模块文档就近放置，`docs/` 负责集中导航与跨模块专题。
- 调整模块文档目录细则：模块根目录仅保留 `README.md` 与 `module_info.yaml`，其余模块文档统一放入模块内 `docs/` 子目录。
- `module_info.yaml` 的 core 兼容字段统一为 `compatible_core_versions`，并使用 semver range（如 `^0.2.0`）。
- 模块版本元数据规则更新：`version` 初始统一为 `0.2.0`，`compatible_core_versions` 初始统一为 `>=0.2.0`。
- API 文档模板增强：每个函数条目至少包含函数名、状态、描述、诞生版本、参数（名称/类型/是否必须）、返回值。
- 架构文档模板改为极简 overview：仅保留设计目标、模块职责、架构/流程图，并要求文档版本与模块版本一致。
- 架构文档模板进一步细化：改为“模块介绍、模块目标、依赖说明、模块职责与边界、架构/流程图”。
- 文档规范补充：README 不维护“下游使用方”信息；非 API/DECISIONS 文档只写当前事实，不写历史沿革。
- 架构文档模板修订：移除“模块基础信息”区块，改为“工作拆分（子模块/管理器 + 职责）”；`DESIGN.md` 作为详细子模块说明文档。
- `infra.discovery`：按模块文档规范补齐 `module_info.yaml` 与 `docs/`（ARCHITECTURE、DESIGN、API、DECISIONS），重写模块 `README.md`。
- `docs/module-doc-standard.md`：§4.3 明确 `API.md` 全仓库统一版式（`### 函数名`、`params` 三列表格、可选参数标 `(可选)`）、复杂 API 的示例放置方式；PR 自检项同步。

---

### v0.2.0 (2026-04-13)

- 新增加了data contract的核心模块，为核心策略和标签模块增加了用户可扩展的数据契约
- 制作了一个最小demo合集，让用户5分钟能跑起来框架
- 在tag和strategy里集成了data contract模块
- 去掉了tag模块写死的多进程分配逻辑，变成可自动通过内存变化分配进程的auto模式
- 增加了所有相关UT

---


---

### v0.1.1 (2026-04-05)

- 修复了数据库配置中配置需要mysql：或者 postgresql：包裹的bug，更新了db的example的配置文件
- 更新了所有的UT，增加coverage，更新了README里的运行pytest的部分

---


---

### v0.1.0 (2026-02-11)

- 首个对外开源的预发布版本；
- 统一许可证为 Apache License 2.0，并清理文档中与之冲突的非商业条款；
- 清理硬编码的本地路径和个人 workspace 配置，完善 Tushare token 等配置指引；
- 新增开源配套文档：`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、`SECURITY.md`、`SUPPORT.md`、`.github` issue/PR 模板；
- 新增基础 CI（GitHub Actions）流水线与测试说明；
- 在 README 中补充项目定位、版本规范说明以及公共 API / 内部实现的边界说明。

---

### v0.0.3 (2026-01-15)

- 🎯 **三层回测架构**：机会枚举 → 价格因子模拟 → 资金分配模拟；
- 💰 **资金分配模拟器**：真实资金约束下的组合回测，支持等资金/等股/Kelly 分配策略；
- 📉 **价格因子模拟器**：无资金约束的信号质量评估，快速验证策略有效性；
- 🏷️ **版本管理系统**：独立的版本控制，支持多轮回测结果对比；
- ⚙️ **配置系统重构**：统一的配置结构，移除向后兼容，更清晰的字段命名；
- 🔄 **模块化优化**：代码拆分和重构，提高可维护性；
- 📊 **结果输出优化**：详细的交易记录、权益曲线、汇总统计；
- 🗄️ **DataManager 重构**：Facade + Service 架构，职责分离，明确性优先；
- 📦 **DataSource 系统**：Handler + Provider 架构，配置驱动、易于扩展，支持多数据源切换；
- 🏷️ **Tag 系统**：Scenario + Tag 三层架构，配置驱动的标签计算框架，支持多进程并行计算；
- 📈 **Indicator 模块**：基于 `pandas-ta-classic`，支持 150+ 技术指标，通用模块设计；
- 🔧 **Infrastructure 完善**：Database 和 Worker 系统优化，多进程安全，自动资源管理。

---

### v0.0.2 (2024-09-25)

- 重构策略框架，支持插件化策略；
- 新增投资目标管理系统；
- 新增自定义结算逻辑支持；
- 新增 Momentum、MeanReversion 策略；
- 优化 RTB 策略（ML 增强版）；
- 完善文档和示例。

---

### v0.0.1 (2024-07-26)

- 从 Node.js 迁移到 Python；
- 重构系统架构；
- 添加多数据源支持。

