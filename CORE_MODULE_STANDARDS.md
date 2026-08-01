# NTQ Core Module Standards - 核心模块创建与维护准则

**版本：** 1.2.0  
**最后更新：** 2026-08-01  
**适用范围：** `core/modules/*`、`core/infra/*`（及其他 core 下按本标准收口的主模块）

> **本文：** 核心模块的创建、维护、测试结构、版本、Facade / 导出等**模块规则**。  
> **文档格式 / 清单 / 位置 / 章节：** 以 [`docs/module-doc-standard.md`](docs/module-doc-standard.md) 为准（文档 SSOT）。  
> **可 copy 骨架：** [`docs/doc_templates/module/`](docs/doc_templates/module/)。

---

## 📋 目的

本文档定义了 NTQ 项目核心模块的创建、维护和清理准则，确保：
- **一致性**：所有核心模块遵循相同的规范
- **可维护性**：强规则优于灵活性，便于长期维护
- **稳定性**：API 契约明确，避免破坏性变更
- **可发现性**：模块结构与契约统一；文档细节见 [模块文档规范](docs/module-doc-standard.md)

---

## 🎯 设计理念（抽象原则）

> 理念是指导原则，不可自动化检查，需要人工判断和决策

### **理念1：收紧核心模块**

> 核心模块需要收紧，不要多个文件提供相同功能的API

**原因：**
- 避免用户混淆，不知道该调用哪个API
- 减少维护成本，不需要同时维护多个入口点
- 确保API契约稳定，不会因为多个入口点导致不一致

**实践：**
- 每个核心模块应该有一个Facade类（对外唯一入口）
- 内部实现私有化（内部Manager不对外暴露）
- 抽象接口明确（所有对外API在抽象类中定义）

---

### **理念2：强规则优于灵活性**

> 核心模块不需要灵活，而是强规则，这样才好维护

**原因：**
- 灵活性导致维护成本增加
- 强规则确保一致性，减少错误
- 用户不需要学习多种方式，简单清晰

**实践：**
- 单一调用方式（所有API使用类方法）
- 统一命名规范（遵循CODE_STYLE.md）
- 统一错误处理（所有API使用相同的错误处理策略）

---

### **理念3：术语统一**

> 核心模块需要有术语表，术语需要统一，不要出现多个术语描述同一个事物

**原因：**
- 避免混淆，不同模块使用相同的术语
- 减少沟通成本，术语一致便于理解

**实践：**
- 定义术语表（glossary.yaml）
- 遵循术语表（所有代码、文档、注释遵循术语表）
- 及时更新（发现新的术语冲突，及时更新术语表）

---

### **理念4：版本管理**

> 核心模块需要有版本号：`MAJOR.MINOR.PATCH`（见指标 4 / 11）

**原因：**
- 明确模块版本，便于管理依赖
- 记录变更历史，便于追溯

**实践：**
- 小 / 中 / 大版本语义见指标 11（NTQ 约定：新 API 可进 PATCH；破坏性进 MINOR；MAJOR 随 core）
- 版本一致性（`module_info` 与各文档文首一致）
- 每次 bump `version` 须追加 `changelog`

---

### **理念5：依赖管理**

> 核心模块需要明确依赖关系，避免循环依赖

**原因：**
- 依赖关系清晰，便于理解模块关系
- 避免循环依赖，确保模块独立性

**实践：**
- 依赖列表明确（module_info.yaml中明确依赖）
- 避免循环依赖（依赖关系应该是单向的）
- 最小依赖原则（尽量减少依赖数量）

---

### **理念6：性能考虑**

> 核心模块需要考虑性能，避免过度抽象

**原因：**
- 核心模块使用频率高，性能影响大
- 过度抽象导致性能下降

**实践：**
- 避免过度抽象（不要为了"灵活性"过度设计）
- 合理使用缓存（如 PathManager 的 userspace 缓存）
- 调度参数用 dataclass 在入口一次 `validate()` / `resolve()`，避免 dict 在内部重复校验

---

### **理念7：配置边界清晰**

> 核心模块只定义 base defaults + validate/resolve；业务调优配置归属应用层，用户 settings 不可覆盖运行参数

**原因：**
- 避免 global worker.json 与模块 settings 多层 merge 导致行为不可预期
- 性能调优由基准测试得出，不应暴露给用户随意改动
- engine 入口一次 validate，内部不再散落 `"auto"` 判断

**实践（以 backtest_engine 为参考）：**
- engine：`EntityBasedPerformance.base()` + 应用方 override → `validate()` → `resolve_for_planning()`
- 应用层：模块内 `settings/dispatch.yaml`（或等价常量），run 前 load 并传入 `BacktestEngine.run(performance=...)`
- 用户 settings：只含业务字段（如 `update_mode`、`run_options.dry_run`），**禁止** `settings["performance"]`
- engine **不**读取 `core/default_config/worker.json` 的 dispatch 段
- infra 能力（如 `MachineInfo`）直接从 `core.infra.*` 导入，**禁止**在模块内建 re-export 空壳文件

---

### **理念8：进度与可观测性内聚**

> 调度类核心模块在 engine 层统一计算进度；显示开关与计算逻辑分离

**实践：**
- 进度始终计算（分阶段权重 + execute 单元计数）
- API 参数如 `enable_progress_display` 仅控制 CMD/日志输出，不影响内部计数
- slice 等细粒度进度通过 engine 注入的 hook（如 `_engine_on_execute_unit_done`）由 orchestrator 回调，不重复在业务层拼 percent

---

## ✅ 硬性指标（可自动化检查）

> 硬性指标是具体要求，可以自动化检查，确保模块符合规范

### **指标1：文件结构要求**

> 核心模块必须有完整的文件结构（代码契约 + 元数据；文档见指标3）

**必需文件：**

| 文件路径 | 文件类型 | 说明 | 检查方式 |
|---------|---------|------|---------|
| `<module_name>.py` | Python文件 | 模块主文件 / Facade 实现 | 文件名与模块目录名一致 |
| `__init__.py` | Python文件 | 导出 Facade 类 | 文件存在，包含 Facade 导出 |
| `module_info.yaml` | YAML文件 | 模块元数据 | 文件存在 |
| `glossary.yaml` | YAML文件 | 统一术语表 | 文件存在 |
| `contracts.py` | Python文件 | 跨模块契约类型（dataclass / enum） | 有对外类型时必须存在 |

**遗留说明：** 人读 API 统一为模块根 `API.md`（细则与迁移见 [模块文档规范](docs/module-doc-standard.md)）；存量 `api.yaml` / `docs/API.md` 迁完即删。

---

### **指标2：测试结构与文件要求**

> 测试分三块：**模块根 `__test__`**（公开契约 + 可选集成/冒烟）、**功能包 `__test__`**（私有单测）、**模块根 `__performance__/`**（正式本模块 benchmark，可选）。  
> 单测用例索引为 **`TEST_CASES.md`**（取代 `test_cases.yaml`）；正文结构见 [模块文档规范 §4](docs/module-doc-standard.md)。  
> 性能目录骨架见 [`docs/doc_templates/module/__performance__/`](docs/doc_templates/module/__performance__/)。

**目录职责：**

| 位置 | 放什么 | 不放什么 |
|------|--------|----------|
| `<module>/__test__/` | **`test_api.py`（必须）**；可选 `test_integration_*.py`、**薄** `test_performance_*.py`（CI 冒烟）；`TEST_CASES.md` | 正式 bench 的大输入/历史结果（→ `__performance__/`）；包内细单测 |
| `<package>/__test__/` | 该包 **unit** + `TEST_CASES.md` | 超出该包职责；测其他模块行为 |
| `<module>/__performance__/` | 本模块正式性能：固定输入、脚本、分版本结果、`CASES.md` | e2e/跨模块（→ `devtools/performance/`）；普通 API 单测 |

```text
<module_root>/
├── API.md
├── __test__/                          # 模块级（轻量，默认可进 CI）
│   ├── TEST_CASES.md
│   ├── test_api.py
│   ├── test_integration_*.py          # 可选
│   └── test_performance_*.py          # 可选：短冒烟，非正式 bench
├── __performance__/                   # 可选：本模块正式 benchmark
│   ├── README.md                      # 怎么跑、机器假设、指标含义
│   ├── CASES.md                       # 性能 case 文档
│   ├── inputs/                        # 固定输入（或生成脚本 + 说明/校验）
│   ├── scripts/                       # benchmark 入口脚本
│   └── results/
│       └── <module.version>/          # 或 <date>_<gitsha>/；便于对比
└── core/<feature>/__test__/           # 功能包级（按需）
    ├── TEST_CASES.md
    └── test_*.py
```

**模块根 `__test__` 允许的测试类型：**

| 类型 | 文件模式 | 说明 |
|------|----------|------|
| API（必须） | `test_api.py` | 与 `API.md` 公开入口对应；抓 breaking change |
| Integration（可选） | `test_integration_*.py` | 跨多个内部包、仍属本模块行为 |
| Performance 冒烟（可选） | `test_performance_*.py` | **短、可 CI**；断言阈值/超时等，不替代 `__performance__/` |

#### `__performance__/`（可选；正式本模块性能）

> 与 `__test__` **分离**：大输入、脚本、多版本结果不进单测目录。  
> 目录名固定为 **`__performance__/`**（与 `__test__` 对称）。  
> 文档写法见 [模块文档规范 §4](docs/module-doc-standard.md)；骨架：[`__performance__/`](docs/doc_templates/module/__performance__/)。

| 子路径 | 内容 |
|--------|------|
| `README.md` | 如何运行、环境/机器假设、指标含义、与 `devtools/performance` 的边界 |
| `CASES.md` | 性能场景与 case；对应 `scripts/`；模板见上 |
| `inputs/` | 固定输入数据，或「生成脚本 + 来源/校验和」说明（避免无说明的巨型二进制进库） |
| `scripts/` | 正式 benchmark 入口（非 pytest 冒烟） |
| `results/<version>/` | 按 **模块 version**（或 `date_gitsha`）归档的结果，便于对比 |

**结果提交约定：**

- 可提交**官方基线**（如某版本 `results/0.5.0/`）。
- 本地噪声跑分默认不提交；可用 `.gitignore` 忽略 `results/_local/` 等。
- 对比时以同机器假设 / README 中的环境说明为准。

**Performance 内外分工：**

| 放哪里 | 判据 |
|--------|------|
| `__test__/test_performance_*.py` | CI 可承受的短冒烟 |
| `__performance__/` | 本模块正式 bench：固定输入 + 脚本 + 分版本结果；仅依赖本模块公开 API（+ 本地 fixture） |
| `devtools/performance/` | e2e、跨模块、或强依赖全栈/多模块场景 |

**CI：** 默认跑 `__test__/`；`__performance__/` 为手动或 nightly，不拖慢常规 PR（除非模块自行约定）。

**Scope 硬性约定（包内 `__test__`）：**

- 断言范围不得超出**当前包目录**的职责。
- 可调用依赖模块的**公开 API** 作夹具；**不得**把依赖模块的正确性当作本 suite 的测试目标。

**API 测试硬性约定：**

- 模块根 `API.md` 与 `__test__/test_api.py` **成对**；缺一不可。
- `API.md` 中每个对外入口须有对应 case（按 API 节/入口映射即可，不必一方法一文件）。
- API 不破坏时，内部重构 / 包内单测调整 → 版本规则上可走**小版本**；破坏公开 API → **中版本**，并同步 `API.md` + `test_api.py` + `__test__/TEST_CASES.md`。

**`TEST_CASES.md`（每个 `__test__` 目录一份）：**

| 内容 | 要求 |
|------|------|
| 覆盖版本 | = `module_info.yaml` 的 `version`（或注明兼容范围） |
| Scope / 边界 | 负责 / 不负责；允许的测试类型 |
| Scenario → Case | Case 名 = pytest 函数名；标明所属 `test_*.py` |
| 与 API 对齐 | 根目录 API suite 须能映射到 `API.md` |
| 性能正式 case | 写在 `__performance__/CASES.md`；根 `TEST_CASES` 可仅链接，不复制大段 |

**遗留：** 存量 `__test__/test_cases.yaml` 迁移为 `TEST_CASES.md` 后删除；模块专属旧 bench 从 `devtools/performance/<module>/` 迁入该模块 `__performance__/`。

---

### **指标3：文档文件要求**

> 核心模块必须有文档。**格式、清单、放置、章节、写作与维护触发**以文档 SSOT 为准：  
> → [`docs/module-doc-standard.md`](docs/module-doc-standard.md)

**与模块规则交叉的硬性点（便于本文件检查清单）：**

| 要求 | 说明 |
|------|------|
| 必需文件 | 根：`README.md`、`API.md`、`glossary.yaml`、`module_info.yaml`；`docs/ARCHITECTURE.md` |
| API 位置 | 人读 API **仅**模块根 `API.md`（不得只放 `docs/API.md`） |
| API ↔ 测试 | `API.md` 公开入口必须有 `__test__/test_api.py` 覆盖（见指标 2） |
| 模板 | 整棵 copy [`docs/doc_templates/module/`](docs/doc_templates/module/) |

细则（受众分工、可选文档、notes、交叉链接、各文档结构）不在本文重复。

---

### **指标4：module_info.yaml内容要求**

> 字段结构见 [`module_info.yaml`](docs/doc_templates/module/module_info.yaml)（保持原样，不增删必填字段）  
> 位置：模块根目录 `module_info.yaml`

**必需属性：**

| 属性名 | 类型 | 说明 | 检查方式 |
|--------|------|------|---------|
| `name` | string | 模块名称（如 `infra.db`） | 属性存在 |
| `version` | string | 模块版本 `MAJOR.MINOR.PATCH` | 属性存在，格式正确 |
| `compatible_core_versions` | string | 兼容的 **core** 版本 range（与模块 `version` 独立） | 属性存在 |
| `description` | string | 模块描述 | 属性存在 |
| `dependencies` | list | 模块级依赖列表 | 属性存在 |
| `changelog` | list | 本模块变更记录 | 至少一条；`changelog[0].version` = 顶层 `version` |

**`changelog` 格式：** 新 → 旧；每条含 `version` + `changes`（字符串列表）。

**版本一致性：** `module_info.yaml` 的 `version`、`changelog[0].version` 与各文档文首版本一致（文档侧细则见 [模块文档规范](docs/module-doc-standard.md)）。

**版本 bump 语义：** 见 **指标 11**（小 / 中 / 大）。

---

### **指标5：模块根 `API.md` 内容要求**

> `API.md` 的版式、字段与禁止项见文档 SSOT：  
> → [`docs/module-doc-standard.md` §2](docs/module-doc-standard.md)  
> 模块侧硬性：位置在模块根；与 `__test__/test_api.py` 成对（指标 2 / 3）。  
> **稳定性：** core 仍为 `0.x` 时，公开 API 状态最高 `beta`，**禁止** `stable`（细则见文档规范）。

---

### **指标6：api.py内容要求**

> api.py必须定义Facade类和namespace API

**必需内容：**

| 内容 | 类型 | 说明 | 检查方式 |
|------|------|------|---------|
| `模块名.py` | file | 模块主文件 | 文件名与模块名一致（如 discovery.py） |
| `Facade类` | class | 对外唯一入口 | 类名简洁（如 Discovery, ProjectContext） |
| `namespace API` | method | 嵌套结构API | API使用命名空间（如 Discovery.file.xxx） |

**禁止项：**
- ❌ 不使用 api.py 命名（使用模块名.py）
- ❌ 不定义ABC类（使用Facade类）
- ❌ 不使用抽象方法（使用具体实现）
- ❌ 不暴露class和便捷函数

---

### **指标7：__init__.py导出要求**

> __init__.py 仅导出 Facade；对外契约放在根目录独立模块（如 `contracts.py`）

**必需导出：**

| 导出项 | 类型 | 说明 | 检查方式 |
|--------|------|------|---------|
| `Facade类` | class | 对外主入口 | __init__.py 导出 Facade 类 |

**契约模块（根目录，跨模块 import 入口）：**

| 文件 | 导出项 | 说明 |
|------|--------|------|
| `contracts.py` | dataclass / enum | 如 `JobContext`、`JobReport`、`RunProgress` |
| `jobs.py` | helper class | 如 `BacktestJob.from_dict` |

**禁止项：**
- ❌ 不在 __init__.py 堆叠契约 re-export（难以发现、IDE 跳转差）
- ❌ 不导出内部实现类（如 `TimelineExecutor`、`SlicePlanner`）
- ❌ 不导出便捷函数（除非文档明确列为 public API）
- ❌ 不保留向后兼容 proxy 函数
- ❌ 不为 infra 类型建 re-export 空壳（如 `machine_info.py` 仅 `from core.infra import X`）— 调用方直接 import infra

---

### **指标8：文档内容要求**

> 各文档固定章节、写作约束与维护触发见文档 SSOT：  
> → [`docs/module-doc-standard.md` §3](docs/module-doc-standard.md)  
> 模板骨架：[`docs/doc_templates/module/`](docs/doc_templates/module/)

---

### **指标9：文件命名规范**

> 核心模块文件命名必须遵循统一规范

**命名规则：**

| 文件类型 | 命名规范 | 示例 | 检查方式 |
|---------|---------|------|---------|
| 模块名.py | 对外暴露 API | `discovery.py`, `project_context.py` | 文件存在，文件名与模块名一致 |
| 内部实现文件夹 | 使用 `core/` | `core/` 子目录存在 | 不使用 `_impl/`, `modules/` 等命名 |
| 文档文件名 / 位置 | 见文档规范 | README / API 在根；ARCHITECTURE 等在 `docs/` | [模块文档规范](docs/module-doc-standard.md) |

**禁止项：**
- ❌ 不使用 `_impl/` 命名内部实现目录
- ❌ 不使用 `modules/` 命名内部实现目录
- ❌ 根目录不保留冗余文件
- ❌ 文档双源 / API 位置错误：见 [模块文档规范](docs/module-doc-standard.md)

---

### **指标10：API暴露方式**

> 核心模块 API 暴露遵循 Facade 模式；契约类型从根目录独立模块导入

**暴露规则：**

| 要求 | 规范 | 检查方式 |
|------|------|---------|
| 主入口为 Facade 类 | 如 `Discovery`, `BacktestEngine` | __init__.py 导出 Facade |
| 契约 types 独立模块 | dataclass / enum / wire helper | 根目录 `contracts.py` 等 |
| 使用 namespace API（可选） | 如 `Discovery.file.xxx` | 嵌套结构 |
| 不暴露内部 executor/planner | 实现细节留在 `core/` | 跨模块不 import `core/` |
| 不保留向后兼容 proxy | 不提供旧 API 代理函数 | 代码中无兼容 proxy |

**示例：**
```python
# ✅ 推荐：Facade + 根目录契约模块
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks
from core.modules.backtest_engine.core.performance.worker_profile import (
    WorkerProfiles,
    resolve_entity_based_performance_for_profile,
)

result = BacktestEngine.entity_based.run(
    jobs,
    execute_fn,
    performance=resolve_entity_based_performance_for_profile(WorkerProfiles.TAG),
    task_name="tag:demo",
    callbacks=RunCallbacks(on_result=handle_result),
    enable_progress_display=True,
)

# ❌ 禁止：跨模块 import 内部路径
from core.modules.backtest_engine.core.timeline_based.planner import TimelinePlanner

# ❌ 禁止：用户 settings 传入 performance
settings["performance"] = {"max_workers": 8}
```

---

### **指标14：TEST_CASES.md 用例索引**

> 每个 `__test__` 目录维护一份 `TEST_CASES.md`（取代 `test_cases.yaml`）。  
> **正文结构与规则**见 [`docs/module-doc-standard.md` §4](docs/module-doc-standard.md)。  
> 模块侧：存在该文件；Case 名与 pytest 一致；API suite 映射 `API.md`（指标 2）。

---

### **指标11：版本号更新规范**

> 模块 `version` 使用 `MAJOR.MINOR.PATCH`。**这是模块版本，不是**根目录 `CHANGELOG.md` 的 core 版本。  
> 下列约定与经典 semver 不完全相同：请以本表为准。

| 段 | 中文 | 何时递增 | 示例 |
|----|------|----------|------|
| **PATCH**（小版本） | 小 | 修 bug；改注释；**内部**改名/整理；API **稳定性标注**变更（如 `beta→deprecated` 且未删）；**新加**公开 API；其他**无破坏性**改动 | `0.5.0` → `0.5.1` |
| **MINOR**（中版本） | 中 | 改动**已有**（`beta` / 日后 `stable`）公开 API / 配置契约；任何**破坏性**改动（公开符号改名、删 API、改签名/语义/行为） | `0.5.1` → `0.6.0` |
| **MAJOR**（大版本） | 大 | **随 core 大版本**；core 仍为 `0.x` 时模块 MAJOR **保持 0** | core `1.0.0` 时模块可 → `1.0.0` |

**补充约定：**

- **公开符号改名** = 破坏性 → **中版本**；仅模块内部改名 → **小版本**。
- 仅文档笔误、与行为无关的措辞修正：可不 bump；文档与实现对齐的实质性修正 → 至少 **小版本**。
- 同一发布批次多次提交：合并为一次 bump；`changelog` 写清本版本要点。
- bump 后同步：`module_info.version`、`changelog[0]`、相关文档文首版本、`API.md` 中受影响入口的「引入版本」只在新增时填写。

---

### **指标12：代码注释规范**

> docstring 一句话说明「做什么」；签名/类型已表达的信息不重复；对外契约在模块根 `API.md`；概念见 `docs/CONCEPTS.md`（若有）

**注释规则：**

| 注释类型 | 是否保留 | 说明 |
|---------|---------|------|
| 一行 docstring（做什么） | ✅ 保留 | 公开/内部函数均可 |
| 复杂逻辑行内注释 | ✅ 保留 | 解释非显而易见的算法或分支 |
| 冗余 docstring（Args/Returns/Examples） | ❌ 不写 | 类型注解 + 根目录 `API.md` 已覆盖 |
| 冗余 docstring（Note/使用方式） | ❌ 不写 | 见 `docs/CONCEPTS.md` / `docs/ARCHITECTURE.md` |

**示例：**
```python
# ✅ 推荐：只保留必要注释
def calculate_weighted_average(prices: List[float], weights: List[float]) -> float:
    """
    计算加权平均值
    """
    # 使用对数加权避免数值溢出（复杂逻辑需要注释）
    log_weights = np.log(weights + 1e-10)
    return np.sum(prices * np.exp(log_weights)) / np.sum(np.exp(log_weights))

# ❌ 禁止：冗余注释
def find_file(filename: str) -> Path:
    """
    查找文件

    Args:
        filename: 文件名  # ❌ 冗余，已在 API.md 中说明

    Returns:
        文件路径  # ❌ 冗余，已在 API.md 中说明

    Examples:  # ❌ 冗余，已在 API.md 中提供
        >>> find_file("config.yaml")
        /path/to/config.yaml

    Note:  # ❌ 冗余，应在 CONCEPTS / ARCHITECTURE 中说明
        该函数会递归搜索
    """
    pass
```

---

### **指标13：不保留兼容性**

> 核心模块在0.x版本可以颠覆性改动

**兼容性规则：**

| 版本范围 | 允许的改动 | 要求 |
|---------|-----------|------|
| 0.x 版本 | ✅ 颠覆性改动 | 直接改动，不保留旧API |
| 1.x 版本 | ⚠️ 向后兼容 | 保留旧API，添加废弃警告 |
| 2.x+ 版本 | ⚠️ 向后兼容 | 遵循语义化版本规范 |

**实践：**
- ✅ 直接改动，不保留旧API
- ❌ 不保留平铺API作为proxy
- ❌ 不保留旧类名作为alias

**示例：**
```python
# ✅ 推荐：0.x版本直接改动
# 旧版本 0.3.0
# find_file("config.yaml")

# 新版本 0.4.0
# Discovery.file.find_file("config.yaml")

# ❌ 禁止：保留向后兼容proxy
def find_file(*args, **kwargs):
    """已废弃，请使用 Discovery.file.find_file"""
    warnings.warn("find_file is deprecated, use Discovery.file.find_file")
    return Discovery.file.find_file(*args, **kwargs)

# ❌ 禁止：保留旧类名
FileUtils = Discovery  # 不允许alias
```

---

## 📊 自动化检查脚本

### **检查脚本示例**

```python
#!/usr/bin/env python3
"""
核心模块标准检查脚本
"""

import os
import yaml
from pathlib import Path
from typing import List

def check_core_module(module_path: Path) -> List[str]:
    """检查核心模块是否符合标准"""
    errors = []
    
    # 检查必需文件（代码契约 + 文档）
    required_files = [
        "__init__.py",
        "module_info.yaml",
        "glossary.yaml",
        "README.md",
        "API.md",
        "glossary.yaml",
        "module_info.yaml",
        "docs/ARCHITECTURE.md",
        # DESIGN / CONCEPTS / QUICKSTART 可选；DECISIONS 已取消
    ]

    for file in required_files:
        if not (module_path / file).exists():
            errors.append(f"缺少必需文件：{file}")

    # API 文档位置：不得只放在 docs/
    if (module_path / "docs/API.md").exists() and not (module_path / "API.md").exists():
        errors.append("API.md 必须在模块根目录（请从 docs/API.md 迁出）")

    # 遗留双源：迁移期若仍存在 api.yaml，提醒删除
    if (module_path / "api.yaml").exists():
        errors.append("遗留 api.yaml：请迁移至模块根 API.md 后删除")

    # API 文档与测试成对
    if (module_path / "API.md").exists() and not (module_path / "__test__/test_api.py").exists():
        errors.append("API.md 存在但缺少 __test__/test_api.py（公开 API 必须有测试覆盖）")

    # 检查 module_info.yaml 内容
    module_info_path = module_path / "module_info.yaml"
    if module_info_path.exists():
        module_info = yaml.safe_load(module_info_path.read_text())
        required_attrs = [
            "name",
            "version",
            "compatible_core_versions",
            "description",
            "dependencies",
            "changelog",
        ]
        for attr in required_attrs:
            if attr not in module_info:
                errors.append(f"module_info.yaml缺少必需属性：{attr}")

    # 检查测试文件
    test_api_path = module_path / "__test__/test_api.py"
    if not test_api_path.exists():
        errors.append("缺少必需测试文件：__test__/test_api.py")

    test_cases_md = module_path / "__test__/TEST_CASES.md"
    if not test_cases_md.exists():
        errors.append("缺少 __test__/TEST_CASES.md（用例索引；取代 test_cases.yaml）")
    if (module_path / "__test__/test_cases.yaml").exists():
        errors.append("遗留 __test__/test_cases.yaml：请迁移为 TEST_CASES.md 后删除")

    return errors

# 使用示例
module_path = Path("/path/to/core/module")
errors = check_core_module(module_path)
if errors:
    print("❌ 模块不符合标准：")
    for error in errors:
        print(f"  {error}")
else:
    print("✅ 模块符合标准")
```

---

## 🎯 检查清单

### **创建新模块检查清单**

| 检查项 | 类型 | 说明 |
|--------|------|------|
| ✅ 文件结构完整 | 硬性指标 | 代码契约与元数据文件存在 |
| ✅ 测试结构 | 硬性指标 | 根 `__test__`：test_api + TEST_CASES.md；包内单测下沉；正式 bench 用 `__performance__/`（若有） |
| ✅ 文档齐全 | 硬性指标 | 见 [模块文档规范](docs/module-doc-standard.md)；根 README+API+glossary+module_info；docs/ARCHITECTURE |
| ✅ API 有测试覆盖 | 硬性指标 | `__test__/test_api.py` 覆盖 `API.md`；用例见 TEST_CASES.md |
| ✅ 从模板 copy | 硬性指标 | 整棵 copy [`docs/doc_templates/module/`](docs/doc_templates/module/)；章节见文档规范 |
| ✅ module_info.yaml 属性完整 | 硬性指标 | 所有必需属性存在 |
| ✅ Facade + contracts | 硬性指标 | `__init__.py` 导出 Facade；契约在 `contracts.py` |
| ✅ 收紧核心模块 | 理念 | Facade 模式，单一入口点 |
| ✅ 术语统一 | 理念 | 遵循 glossary.yaml |
| ✅ 版本管理 | 理念 | 语义化版本，changelog 记录 |
| ✅ 依赖管理 | 理念 | 明确依赖关系 |

---

### **维护模块检查清单**

| 检查项 | 类型 | 说明 |
|--------|------|------|
| ✅ 版本号一致 | 硬性指标 | module_info 与各文档文首版本一致 |
| ✅ changelog 更新 | 硬性指标 | 记录所有改动 |
| ✅ 文档同步更新 | 硬性指标 | 见 [模块文档规范](docs/module-doc-standard.md) 维护触发 |
| ✅ 根目录 `API.md` 与实现一致 | 硬性指标 | 签名 / 状态 / 参数表对齐代码 |
| ✅ API 测试同步 | 硬性指标 | `__test__/test_api.py` 覆盖文档中的公开入口 |
| ✅ 无 api.yaml / docs/API.md 双源 | 硬性指标 | 迁移完成后只保留模块根 `API.md` |
| ✅ 测试通过 | 硬性指标 | 所有测试通过 |
| ✅ 性能考虑 | 理念 | 避免过度抽象 |
| ✅ 强规则优于灵活性 | 理念 | 单一调用方式 |

---

### **清理模块检查清单**

| 检查项 | 类型 | 说明 |
|--------|------|------|
| ✅ 删除冗余 API | 理念 | 不要多个文件提供相同功能的 API |
| ✅ TEST_CASES.md 对齐 | 硬性指标 | scenario/case 与 pytest 函数及文件一致；无遗留 test_cases.yaml |
| ✅ 删除冗余代码 | 理念 | 无 re-export 空壳、无未使用 default/merge 层 |
| ✅ 文档与代码一致 | 硬性指标 | 不用已退役模块名 |
| ✅ 删除遗留 api.yaml / docs/API.md | 硬性指标 | 内容已迁入模块根 `API.md`，且有测试覆盖 |

---

## 📝 总结

**核心模块的标准分为两部分：**

1. **设计理念（抽象原则）**：指导原则，需要人工判断  
   收紧核心模块 · 强规则优于灵活性 · 术语统一 · 版本管理 · 依赖管理 · 性能考虑 · 配置边界清晰 · 进度与可观测性内聚

2. **硬性指标（可自动化检查）**：具体要求  
   文件结构 · 测试 · module_info · Facade/`__init__.py` · **API.md 必须有 test 覆盖** · 文档清单交叉点见指标 3

**文档：** 格式 / 放置 / 章节以 [`docs/module-doc-standard.md`](docs/module-doc-standard.md) 为准。

---

**参考文档：**
- [`docs/module-doc-standard.md`](docs/module-doc-standard.md) — 模块文档规范（文档 SSOT）
- [`docs/doc_templates/module/`](docs/doc_templates/module/) — 可 copy 骨架
- [CODE_STYLE.md](CODE_STYLE.md) — 代码风格
- [`docs/README.md`](docs/README.md) — 仓库文档导航

---

**最后更新：** 2026-08-01  
**维护者：** NTQ Team

**模块参考（迁移目标态，非全部已达标）：** `core/modules/backtest_engine`、`core/modules/data_contract`、`core/infra/db`（整改时以本文 + [模块文档规范](docs/module-doc-standard.md) + 模板为准）