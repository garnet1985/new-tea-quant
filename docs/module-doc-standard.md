# 模块文档规范

**版本：** 1.2.0  
**最后更新：** 2026-08-01  
**适用范围：** `core/modules/*`、`core/infra/*`（及其他按 core 模块标准收口的主模块）的**文档**

> **文档 SSOT：** 模块文档的格式、清单、位置与维护规则以**本文**为准。  
> **模块规则（代码 / 测试结构 / 版本 / Facade 等）：** [`CORE_MODULE_STANDARDS.md`](../CORE_MODULE_STANDARDS.md)  
> **可 copy 骨架：** [`docs/doc_templates/module/`](doc_templates/module/)（与真实模块同结构；整棵 copy 后替换 `<xxx>`，删除不需要的可选文件）

**命名迁移：** `OVERVIEW` → `docs/CONCEPTS.md`；`DECISIONS` → `docs/DESIGN.md`；glossary 在模块根；临时笔记 → `docs/notes/`；用例索引 → `__test__/TEST_CASES.md`；本模块正式性能 → `__performance__/`（e2e 仍在 `devtools/performance`）。

---

## 1. 放置策略与清单

> 细节文档就近放在模块内；仓库根 `docs/` 只放全局准则 / 总览 / 模板，**不**承载单模块实现细节。

| 位置 | 职责 |
|------|------|
| 模块根 `README.md` | **是什么 / 干什么**：**纯文字**介绍；**不含**代码块 |
| 模块根 `API.md` | **怎么调**：公开调用面；与 `__test__/test_api.py` 成对 |
| 模块根 `QUICKSTART.md` | **可选**；最短可运行路径 |
| 模块根 `glossary.yaml` | **名词表**：定义 + aliases + avoid；与 CONCEPTS 分离 |
| 模块根 `module_info.yaml` | 模块元数据（字段见 [CORE 指标 4](../CORE_MODULE_STANDARDS.md)） |
| 模块 `docs/ARCHITECTURE.md` | 高阶已定结论：结构图、架构图、数据流（若有） |
| 模块 `docs/DESIGN.md` | **可选**；设计点（初衷/背景/多方案/决定）；已合并原 DECISIONS |
| 模块 `docs/CONCEPTS.md` | **可选**；运作原理与多步骤关系（**不是**词条表） |
| 模块根 `__performance__/` | **可选**；正式本模块性能（目录结构见 [CORE 指标 2](../CORE_MODULE_STANDARDS.md)） |
| 仓库根 `docs/` | 全局文档、模块准则、本文、可 copy 模板 |

**根目录 vs `docs/`（硬性）：** 若存在下列文件，**必须**在模块根：`README.md`、`API.md`、`QUICKSTART.md`、`glossary.yaml`、`module_info.yaml`。标准模块文档（`ARCHITECTURE` / `DESIGN` / `CONCEPTS`）放在模块 `docs/` 根下（与 `notes/` 同级）。正式性能套件在模块根 `__performance__/`（不要放进 `docs/notes/`）。

**临时 / 开发者自用笔记：** 不设模板、不进 must 清单。草稿、边界碎记、迁移草稿、用完即删的材料等，**一律放在** `docs/notes/`（可再分子目录）。

- 不要求与 `module_info` 版本对齐，不要求交叉链接齐全。
- **不要**把正式文档（README / API / ARCHITECTURE 等）放进 `notes/`；`notes/` 内容不作为对外契约。
- 例：原 `BOUNDARY_NOTES.md`、一次性 ROADMAP 草稿 → `docs/notes/`。

### 必需文档

| 文件路径 | 受众 | 说明 | 检查方式 |
|---------|------|------|---------|
| `README.md`（根） | 使用者 | 是什么、干什么 | 文件在模块根 |
| `API.md`（根） | 调用方 | 公开接口；须有测试覆盖 | 模块根 + `__test__/test_api.py` |
| `glossary.yaml`（根） | 全员 | 名词定义、aliases、avoid | 文件在模块根 |
| `module_info.yaml`（根） | 维护者 | 元数据 | 见 CORE 指标 4 |
| `docs/ARCHITECTURE.md` | 维护者 | 结构图、架构图、数据流（若有）；有版本 | 在 `docs/` |

### 可选文档

| 文件路径 | 受众 | 说明 | 何时需要 |
|---------|------|------|---------|
| `QUICKSTART.md`（根） | 要马上跑起来的人 | 最短可运行路径 | API 单条举例不够时 |
| `docs/CONCEPTS.md` | 要懂原理的人 | 运作原理、多步骤关系（非词条表） | 复杂模块 |
| `docs/DESIGN.md` | 维护者 | 设计点：初衷/背景/多方案/决定（含原 DECISIONS） | 有重要选型时 |

### 受众分工

| 目标 | 文档 |
|------|------|
| 是什么、干什么 | `README.md` |
| 名词 / 别名 / 易混名 | `glossary.yaml`（与 CONCEPTS **分开**） |
| 工作原理、多步骤关系 | `docs/CONCEPTS.md`（可选） |
| 快速上手 | `QUICKSTART.md`（可选）+ `API.md` |
| 正确调用 | `API.md` |
| 高阶已定架构 | `docs/ARCHITECTURE.md` |
| 设计选型与决定 | `docs/DESIGN.md`（可选） |

### 模板用法

新建或整改模块时，整棵 copy [`doc_templates/module/`](doc_templates/module/) 到目标模块根，将 `<xxx>` 占位符替换为模块内容；不需要的可选文件（`QUICKSTART` / `docs/CONCEPTS` / `docs/DESIGN` / `__performance__/`）整份删除。固定章节以骨架内文件为准。

### 命名与位置

- 根目录文件名固定；`docs/` 下 `ARCHITECTURE.md` / `DESIGN.md` / `CONCEPTS.md` 使用大写（不要小写变体）。
- **不再使用** `DECISIONS.md`（内容并入 `DESIGN.md`）。
- ❌ 不并行维护 `api.yaml` / `docs/API.md` 与根目录 `API.md` 多套 API 真源。
- ❌ 不把唯一人读 API 文档只放在 `docs/` 而模块根缺失 `API.md`。

### ARCHITECTURE vs DESIGN

| | ARCHITECTURE | DESIGN（可选） |
|--|--------------|----------------|
| 抽象层级 | High level | 具体设计点 |
| 内容 | **已定结论**（结构图、架构图、数据流） | 初衷、背景、**多方案**、决定（按时间追加） |
| 版本 | 必须 | 有则必须 |

### glossary vs CONCEPTS

glossary = 词条（定义/别名/易混）；CONCEPTS = 原理与关系叙述。二者**不合并**。

### 交叉链接（最低要求）

- `README.md` 链到 `API.md`、`glossary.yaml`、`docs/ARCHITECTURE.md`；若有则链 QUICKSTART / docs/CONCEPTS / docs/DESIGN
- `docs/ARCHITECTURE.md` 链到 `../API.md`、`../glossary.yaml`；若有 DESIGN / CONCEPTS 则链

### 版本一致性

`module_info.yaml` 的 `version`、`changelog[0].version`，以及 `API.md` / `docs/ARCHITECTURE.md` / `glossary.yaml` 头注释版本（及若存在的 `DESIGN` / `docs/CONCEPTS` / `QUICKSTART`）必须一致。版本 bump 语义见 [CORE 指标 11](../CORE_MODULE_STANDARDS.md)。

---

## 2. 模块根 `API.md` 内容

> **位置（硬性）：** `API.md` 必须放在**模块根目录**（与 `README.md`、`module_info.yaml`、`<module>.py` 同级），**不得**只放在 `docs/API.md`。  
> **测试（硬性）：** 与 `__test__/test_api.py` 成对；`API.md` 声明的公开 API **必须有测试覆盖**（测试目录见 [CORE 指标 2](../CORE_MODULE_STANDARDS.md)）。  
> 人读 API 只维护这一份；不要求、不并行维护根目录 `api.yaml`。  
> 版式以 [`doc_templates/module/API.md`](doc_templates/module/API.md) 为准。

**文首：**

- 模块显示名、`**版本：**`（= `module_info.yaml` 的 `version`）
- `**最低支持核心版本：**`（= `module_info.yaml` 的 `compatible_core_versions`）
- 说明：本文件是公开调用面的唯一人读文档；所列入口须有 `__test__/test_api.py` 覆盖

**层级（固定）：**

```text
## <ClassName>                 # Facade / 公开类 / 契约类型
### <namespace>                # 可选；无 namespace 则省略
#### <method_name>             # 无 namespace 时方法用 ###
```

**每个方法固定块：**

1. 标题：`#### <method_name>`（或无 namespace 时的 `### <method_name>`）
2. 下一行：反引号完整签名（含默认值与返回注解，与代码一致）
3. 列表字段（键名固定）：
   - **类型：** `instance` / `classmethod` / `static`
   - **状态：** `experimental` / `beta` / `stable` / `deprecated`
   - **引入版本：** 该入口引入时的模块版本
   - **描述：** 一句话职责
   - **参数：** 无参写 `无`；有参用三列表格；可选参数名字列标 `(可选)`
   - **返回值：** 单值一行 `类型 — 语义`；多字段再用表格
4. 可选：**错误与异常：**、**举例：**

**禁止项：**

- ❌ 不写内部私有方法（不出现 `internal`）
- ❌ 不与 `CONCEPTS.md` / `ARCHITECTURE.md` 大段重复
- ❌ 不并行维护第二份 API 真源（`api.yaml`、`docs/API.md` 等）
- ❌ 不在无 `__test__/test_api.py` 覆盖的情况下宣称 API 已稳定对外

**遗留：** 历史上部分模块使用根目录 `api.yaml` 或 `docs/API.md`。自 **1.2.0** 起统一为模块根 `API.md`；存量迁移完成后删除，标准不再要求。

---

## 3. 各文档内容结构

> 细节与 `<placeholder>` 以 [`doc_templates/module/`](doc_templates/module/) 为准。

| 文档 | 必需内容 | 检查方式 |
|------|---------|---------|
| `README.md` | 见下「README 结构」；偏使用者 | 含必须章节；版式见模板 |
| `glossary.yaml`（根） | 见下「glossary 结构」 | terms 含 definition；建议 aliases/avoid |
| `QUICKSTART.md`（根，可选） | 见下「QUICKSTART 结构」 | 有则含最小示例 |
| `docs/CONCEPTS.md`（可选） | 见下「CONCEPTS 结构」；原理与关系 | 有则文首有版本；非词条表 |
| `docs/ARCHITECTURE.md` | 见下「ARCHITECTURE 结构」 | 文首有版本；结构图 + 架构图 |
| `docs/DESIGN.md`（可选） | 见下「DESIGN 结构」；含原 DECISIONS | 有则每点四段齐全 |
| `API.md`（模块根） | 见上文 §2；且有 `__test__/test_api.py` 覆盖 | 签名与代码一致；测试存在 |

### `README.md`（纯文字；模板见 [`README.md`](doc_templates/module/README.md)）

| 章节 | 必须 / 可选 | 说明 |
|------|------------|------|
| 标题 + 一句话职责 | 必须 | `# <Display>（\`<namespace.module>\`）` + 一行做什么 |
| 适用场景 | 必须 | 2～4 条文字 |
| 模块依赖 | 必须 | 对齐 `module_info.yaml`；无则写「无」；不贴代码 |
| 设计初衷 | 可选 | 解决什么问题 / 不做什么；短；不写未来规划 |
| 常见问题 | 可选 | 短文字 Q&A；名词 → glossary；原理 → docs/CONCEPTS；调用 → API |
| 相关文档 | 必须 | 链到 `API.md`、`glossary.yaml`、`docs/ARCHITECTURE.md`；若有则链其余 |

### `docs/CONCEPTS.md`（可选；模板见 [`docs/CONCEPTS.md`](doc_templates/module/docs/CONCEPTS.md)）

> 专为**复杂模块**。写运作原理与多步骤关系。  
> **不要**当词典（→ `glossary.yaml`）、不要目录树（→ ARCHITECTURE）、不要完整 API。  
> 简单模块可省略。

| 章节 | 必须 / 可选 | 说明 |
|------|------------|------|
| 文首（模块名 + 版本 + 本文补充什么） | 有则必须 | 版本 = `module_info.yaml`；链到 README / API |
| 核心概念 / 主链路（可多节） | 有则必须 | 概念含义、步骤关系、模式差异；可用极短示意代码 |
| 相关文档 | 有则必须 | README、API.md、docs/*、glossary.yaml |

### `glossary.yaml`（模板见 [`glossary.yaml`](doc_templates/module/glossary.yaml)）

> 解释模块名词；同一事物在不同背景下的叫法用 `aliases` / `avoid` 区分。  
> **不与** `docs/CONCEPTS.md` 合并。

| 字段 | 说明 |
|------|------|
| `terms.<Name>.definition` | 本模块中的含义 |
| `terms.<Name>.aliases` | 可接受别名 / 其他上下文叫法 |
| `terms.<Name>.avoid` | 易混淆、不应混用的名称 |

### `QUICKSTART.md`（可选；模板见 [`QUICKSTART.md`](doc_templates/module/QUICKSTART.md)）

> 只写**一条**最短主路径。API 单条举例已够用时可**省略**。

| 章节 | 必须 / 可选 | 说明 |
|------|------------|------|
| 文首（模块名 + 版本 + 覆盖哪条路径） | 有则必须 | 版本 = `module_info.yaml` |
| 前置条件 | 有则必须 | 可写「无特殊前置」 |
| 最小示例 + 预期结果 | 有则必须 | 可运行代码；与实现一致 |
| 下一步 | 有则必须 | 链到 API、glossary；（若有）docs/CONCEPTS；README；pytest |

### `docs/ARCHITECTURE.md`（模板见 [`docs/ARCHITECTURE.md`](doc_templates/module/docs/ARCHITECTURE.md)）

> **High level + 已定结论**。不写方案对比（→ DESIGN）。**必须有版本。**

| 章节 | 必须 / 可选 | 说明 |
|------|------------|------|
| 文首版本 + 定位 | 必须 | 版本 = `module_info.yaml` |
| 职责与边界（In / Out） | 必须 | 已定结论 |
| 模块结构图 | 必须 | 目录 / 包结构 |
| 架构图 | 必须 | 组件 / 分层 / 主调用关系 |
| 数据流 | 可选 | 有显著数据流时写 |
| 依赖 | 建议 | 对齐 `module_info.yaml` |
| 相关文档 | 必须 | API、glossary；（若有）DESIGN / CONCEPTS |

### `docs/DESIGN.md`（可选；模板见 [`docs/DESIGN.md`](doc_templates/module/docs/DESIGN.md)）

> 按**设计点**组织。每点必须含四段。无必要设计点时**省略整文件**。

| 每设计点章节 | 必须 |
|-------------|------|
| 设计初衷 | 解决什么问题 |
| 设计背景 | 约束与上下文 |
| 解决方案 | 多个方案及优劣 |
| 决定 | 采用哪案、理由、影响 |

### 写作约束

- 中文为主，英文术语可括注；短句，避免营销腔
- **缩写与生僻英文须可读：** 如 `NTQ`（New Tea Quant）、`Facade`（门面：对外统一入口）等，读者未必熟悉。做法二选一或并用：  
  1）**首次出现**用中文释义或括注全称；  
  2）收入本模块 [`glossary.yaml`](doc_templates/module/glossary.yaml)，正文可写「见术语表」。  
  不要在 README 首句堆未解释的英文黑话。
- **README 尽量不出现代码块**；上手代码放 `QUICKSTART`（若有）或 `API.md` 举例；原理放 `CONCEPTS`（若有）
- 非 `API.md` / `docs/DESIGN.md` 不写历史沿革，只描述当前事实（DESIGN 内按设计点追加历史）
- 避免多文档大段重复：重复处用相对链接
- `QUICKSTART` / `API.md`（及 CONCEPTS 内示意代码）须可运行或明确标注占位
- 所有相对链接须在仓库内可打开
- README **不写**路线图 / 大段原理 / 上手教程（分属路线图文、CONCEPTS、QUICKSTART）

### 维护触发（满足任一即同步文档）

- 公共 API 变更（新增、删除、参数变化）
- 模块职责边界变化
- 关键流程变化（执行链路、数据流、存储结构）
- 配置结构变化（字段、默认值、语义）

---

## 4. `TEST_CASES.md` 与性能文档

### `__test__/TEST_CASES.md`

> 每个 `__test__` 目录维护一份；**取代** `test_cases.yaml`。  
> 模板：[`__test__/TEST_CASES.md`](doc_templates/module/__test__/TEST_CASES.md)。  
> 测试类型与目录职责见 [CORE 指标 2](../CORE_MODULE_STANDARDS.md)。

**固定结构：** 文首（模块 / 覆盖版本 / 路径）→ Scope → 边界 → 若干 `## Scenario` → 其下 Case 表（函数名 / 文件 / 说明）。

**规则：**

- Case 名与 pytest 函数名一致，且能在表中落到具体 `test_*.py`。
- 模块根 API suite：Scenario/Case 映射 `API.md` 公开面。
- 包内 suite：仅 unit；不测他包/他模块职责。
- 不测本模块职责外的 infra 行为（应在对应 infra 模块的 suite 中测）。

### `__performance__/` 文档（可选）

> 目录与运行约定见 [CORE 指标 2](../CORE_MODULE_STANDARDS.md)。  
> 模板：[`__performance__/README.md`](doc_templates/module/__performance__/README.md)、[`CASES.md`](doc_templates/module/__performance__/CASES.md)。

| 文件 | 内容 |
|------|------|
| `README.md` | 如何运行、环境/机器假设、指标含义、与 `devtools/performance` 的边界 |
| `CASES.md` | 性能场景与 case；对应 `scripts/` |

---

## 5. 文档检查清单（摘要）

| 检查项 | 说明 |
|--------|------|
| 文档齐全 | 根：README + API + glossary + module_info；docs：ARCHITECTURE；（可选）DESIGN / CONCEPTS / QUICKSTART |
| 从模板 copy | 章节与 [`doc_templates/module/`](doc_templates/module/) 一致 |
| 版本号一致 | module_info 与各文档文首版本一致 |
| 文档同步 | 与代码一致；触发见 §3 |
| 根目录 `API.md` | 签名 / 状态 / 参数表对齐代码；有 `test_api.py` |
| 无双源 | 无并行 `api.yaml` / `docs/API.md` |
| `TEST_CASES.md` | scenario/case 与 pytest 对齐；无遗留 `test_cases.yaml` |

模块创建 / 维护 / 清理的完整清单（含代码与测试）见 [`CORE_MODULE_STANDARDS.md`](../CORE_MODULE_STANDARDS.md)。

---

**参考：**

- [`CORE_MODULE_STANDARDS.md`](../CORE_MODULE_STANDARDS.md) — 模块创建与维护准则
- [`doc_templates/module/`](doc_templates/module/) — 可 copy 骨架
- [`docs/README.md`](README.md) — 仓库文档导航
- 术语表示例：[`core/infra/project_context/glossary.yaml`](../core/infra/project_context/glossary.yaml)
