# 模块文档规范

**版本：** 1.6.0  
**最后更新：** 2026-11-19  
**适用范围：** `core/modules/*`、`core/infra/*`（及其他按 core 模块标准收口的主模块）的**文档**

> **文档 SSOT：** 模块文档的格式、清单、位置与维护规则以**本文**为准。  
> **模块规则（代码 / 测试结构 / 版本 / Facade 等）：** [`CORE_MODULE_STANDARDS.md`](../CORE_MODULE_STANDARDS.md)  
> **可 copy 骨架：** [`docs/doc_templates/module/`](doc_templates/module/)（与真实模块同结构；整棵 copy 后替换 `<xxx>`，删除不需要的可选文件）

**命名迁移：** `OVERVIEW` → `docs/CONCEPTS.md`；glossary 在模块根；临时笔记 → `docs/notes/`；用例索引 → `__test__/TEST_CASES.md`；本模块正式性能 → `__performance__/`。**v1.4.0 起**：`docs/DESIGN.md` 废弃，设计目标、方案思路与拍板决策合并进 `docs/DECISIONS.md`（v1.3.0 的 DESIGN/DECISIONS 分离做法撤销）。**v1.5.0 起**：架构图 / 组件关系图以 **Mermaid** 为 SSOT；禁止用 Unicode/ASCII 方框「手绘」流程图（见 §3.1）。**v1.6.0 起**：标准 Markdown 文首统一为两行（模块·版本 + 最低支持核心版本）；站点 `ntq_md2html` 按此解析。

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
| 模块 `docs/DECISIONS.md` | **可选**（有非平凡设计过程或关键选型时必写）；设计目标、方案思路与拍板决策合一——"为什么这么设计、定了什么" |
| 模块 `docs/CONCEPTS.md` | **可选**；运作原理与多步骤关系（**不是**词条表） |
| 模块 `docs/USER_GUIDE.md` | **必须**；用户教程：能干嘛、怎么配、常见坑 |
| 模块根 `__performance__/` | **可选**；正式本模块性能（目录结构见 [CORE 指标 2](../CORE_MODULE_STANDARDS.md)） |
| 仓库根 `docs/` | 全局文档、模块准则、本文、可 copy 模板 |

**根目录 vs `docs/`（硬性）：** 若存在下列文件，**必须**在模块根：`README.md`、`API.md`、`QUICKSTART.md`、`glossary.yaml`、`module_info.yaml`。标准模块文档（`ARCHITECTURE` / `DECISIONS` / `CONCEPTS`）放在模块 `docs/` 根下（与 `notes/` 同级）。正式性能套件在模块根 `__performance__/`（不要放进 `docs/notes/`）。

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
| `docs/USER_GUIDE.md` | 普通用户 | 能干嘛、怎么配、常见坑 | 在 `docs/`；非空 |

### 可选文档

| 文件路径 | 受众 | 说明 | 何时需要 |
|---------|------|------|---------|
| `QUICKSTART.md`（根） | 要马上跑起来的人 | 最短可运行路径 | API 单条举例不够时 |
| `docs/CONCEPTS.md` | 要懂原理的人 | 运作原理、多步骤关系（非词条表） | 复杂模块 |
| `docs/DECISIONS.md` | 维护者 + 未来维护者 | 设计目标、方案思路、拍板决策（每条独立编号） | 有非平凡设计过程或关键选型时 |

### 受众分工

| 目标 | 文档 |
|------|------|
| 是什么、干什么 | `README.md` |
| 名词 / 别名 / 易混名 | `glossary.yaml`（与 CONCEPTS **分开**） |
| 工作原理、多步骤关系 | `docs/CONCEPTS.md`（可选） |
| 快速上手 | `QUICKSTART.md`（可选）+ `API.md` |
| 正确调用 | `API.md` |
| 怎么用、怎么配 | `docs/USER_GUIDE.md`（必须） |
| 高阶已定架构 | `docs/ARCHITECTURE.md` |
| 为什么这么做、定了什么 | `docs/DECISIONS.md`（可选；有选型时必写） |

### 模板用法

新建或整改模块时，整棵 copy [`doc_templates/module/`](doc_templates/module/) 到目标模块根，将 `<xxx>` 占位符替换为模块内容；不需要的可选文件（`QUICKSTART` / `docs/CONCEPTS` / `docs/DECISIONS` / `__performance__/`）整份删除。固定章节以骨架内文件为准。

### 命名与位置

- 根目录文件名固定；`docs/` 下 `ARCHITECTURE.md` / `DECISIONS.md` / `CONCEPTS.md` / `USER_GUIDE.md` 使用大写（不要小写变体）。
- ❌ 不并行维护 `api.yaml` / `docs/API.md` 与根目录 `API.md` 多套 API 真源。
- ❌ 不把唯一人读 API 文档只放在 `docs/` 而模块根缺失 `API.md`。

### ARCHITECTURE vs DECISIONS

| | ARCHITECTURE | DECISIONS（可选） |
|--|--------------|------------------|
| 核心回答 | 长啥样、怎么搭起来的 | "为什么这么设计、定了什么" |
| 内容 | **已定结论**（结构图、架构图、数据流） | 设计目标、方案与思路（候选方案怎么比较）、拍板决策（每条独立编号：是什么 / 为什么选它 / 放弃了什么） |
| 有无历史 | 无（只看当前） | 每条决策独立，天然可追溯 |
| 受众 | 所有人、未来维护者 | 维护者、代码审查者 |
| 版本 | 必须 | 有则必须 |
| 互链 | 被 DECISIONS 引用 | 引用 ARCHITECTURE |

### glossary vs CONCEPTS

glossary = 词条（定义/别名/易混）；CONCEPTS = 原理与关系叙述。二者**不合并**。

### 交叉链接（最低要求）

- `README.md` 链到 `API.md`、`glossary.yaml`、`docs/ARCHITECTURE.md`、`docs/USER_GUIDE.md`；若有则链 QUICKSTART / docs/CONCEPTS / docs/DECISIONS
- `docs/ARCHITECTURE.md` 链到 `../API.md`、`../glossary.yaml`、`USER_GUIDE.md`；若有 DECISIONS / CONCEPTS 则链
- `docs/DECISIONS.md` 的「方案与思路」部分引用 `ARCHITECTURE.md` 的现状描述，不重复粘贴

### 版本一致性

`module_info.yaml` 是模块版本 SSOT。下列位置的版本字段必须与它一致（`devcli.py p` / pack 会检查；非 `--check-only` 时还会按 SSOT 改写文首数字与历史别名）。

**字段名（硬性，禁止别名）：**

| 位置 | 字段 | 例 |
|------|------|----|
| `module_info.yaml` | `version` / `changelog[0].version` | `0.4.0` |
| `module_info.yaml` | `compatible_core_versions` | `>=0.4.5` |
| `module_info.yaml` | `name` | `modules.strategy` / `modules.cli` / `ui` / `bff` / `tables` |
| `module_info.yaml`（可选） | `site_title` / `site_display_title` | 站点文档 Title / Display title；见 CORE 指标 4 |
| Markdown 文首第 1 行 | `**模块：**` · `**版本：**` | `**模块：** `modules.cli` · **版本：** `0.4.5`` |
| Markdown 文首第 2 行 | `**最低支持核心版本：**` | `**最低支持核心版本：** `>=0.5.0`` |
| `glossary.yaml` 头注释 | `# Version:` / `# Compatible-Core:` | `# Version: 0.4.0` / `# Compatible-Core: >=0.5.0` |

禁止用 `**覆盖版本：**`、`**当前基线版本：**`、`**最低核心版本：**` 表示模块 / 核心兼容版本。

**统一 Markdown 文首（紧跟 `#` 标题之后；两行之间空一行）：**

```markdown
**模块：** `<module_info.name>` · **版本：** `<module_info.version>`

**最低支持核心版本：** `<module_info.compatible_core_versions>`
```

**须带标准文首的文件（存在则检查；范围与 `devcli.py p` 一致）：** `API.md`、`glossary.yaml`、`QUICKSTART.md`、`docs/ARCHITECTURE.md`、`docs/CONCEPTS.md`、`__performance__/README.md`、`__performance__/CASES.md`、模块内全部 `**/TEST_CASES.md`。`README.md` 与 `docs/` 根下其它 md（如 `USER_GUIDE` / `DECISIONS`）若文首已写版本字段，也必须是完整两行头且等于 SSOT。`docs/notes/` 不检查。

版本 bump 语义见 [CORE 指标 11](../CORE_MODULE_STANDARDS.md)。

---

## 2. 模块根 `API.md` 内容

> **位置（硬性）：** `API.md` 必须放在**模块根目录**（与 `README.md`、`module_info.yaml`、`<module>.py` 同级），**不得**只放在 `docs/API.md`。  
> **测试（硬性）：** 与 `__test__/test_api.py` 成对；`API.md` 声明的公开 API **必须有测试覆盖**（测试目录见 [CORE 指标 2](../CORE_MODULE_STANDARDS.md)）。  
> 人读 API 只维护这一份；不要求、不并行维护根目录 `api.yaml`。  
> 版式以 [`doc_templates/module/API.md`](doc_templates/module/API.md) 为准。

**文首：**

- 统一两行头：`**模块：**` · `**版本：**` + `**最低支持核心版本：**`（见 §1 版本一致性）
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
   - **状态：** `experimental` / `beta` / `stable` / `deprecated`（取值约束见下「稳定性」）
   - **引入版本：** 该入口引入时的模块版本
   - **描述：** 一句话职责
   - **参数：** 无参写 `无`；有参用三列表格；可选参数名字列标 `(可选)`
   - **返回值：** 单值一行 `类型 — 语义`；多字段再用表格
4. 可选：**错误与异常：**、**举例：**

**稳定性（硬性）：**

| 项目 / core 版本 | 公开 API「状态」允许值 |
|------------------|------------------------|
| core 仍为 `0.x`（未到 **1.0.0**） | 最高 **`beta`**：只许 `experimental` / `beta` / `deprecated`；**禁止**标 `stable` |
| core ≥ **1.0.0** | 可用满档：`experimental` / `beta` / `stable` / `deprecated` |

> 当前仓库 core 为 `0.x`（见 `core/system.json`）。整改与新建模块的 `API.md` 一律按上表：成熟公开入口写 `beta`，不要写 `stable`。

**禁止项：**

- ❌ 不写内部私有方法（不出现 `internal`）
- ❌ 不与 `CONCEPTS.md` / `ARCHITECTURE.md` 大段重复
- ❌ 不并行维护第二份 API 真源（`api.yaml`、`docs/API.md` 等）
- ❌ 不在无 `__test__/test_api.py` 覆盖的情况下把入口标成对外可用（`beta` / 日后 `stable`）
- ❌ core 未到 1.0 时把任何公开入口标成 `stable`

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
| `docs/DECISIONS.md`（可选） | 见下「DECISIONS 结构」；设计目标 + 方案思路 + 拍板决策 | 有则有版本 |
| `docs/USER_GUIDE.md` | 见下「USER_GUIDE 结构」 | 有则有版本；非空 |
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

> **High level + 已定结论**。不写方案对比（→ DECISIONS）。**必须有版本。**  
> 图示写法见下 **§3.1**。

| 章节 | 必须 / 可选 | 说明 |
|------|------------|------|
| 文首版本 + 定位 | 必须 | 版本 = `module_info.yaml` |
| 职责与边界（负责 / 不负责） | 必须 | 已定结论；勿用 In/Out of scope 作标题 |
| 模块结构图 | 必须 | 目录 / 包结构（` ```text ` 树即可） |
| 架构图 | 必须 | 组件 / 分层 / 主调用关系（**必须** ` ```mermaid `） |
| 数据流 | 可选 | 有显著数据流时写（短步骤可用 `text`；关系复杂则用 Mermaid） |
| 依赖 | 建议 | 对齐 `module_info.yaml` |
| 相关文档 | 必须 | API、glossary；（若有）DECISIONS / CONCEPTS |

### 3.1 图示约定（Mermaid SSOT）

> 目标：仓库内架构图可在 GitHub / IDE / 官网文档管道中稳定渲染；**不再**依赖自研 ASCII 方框解析。

| 用途 | 写法 | 说明 |
|------|------|------|
| **架构图 / 组件关系 / 分层调用** | **` ```mermaid `** | **SSOT**。优先 `flowchart TB` 或 `flowchart LR`；节点用短 id + 方括号标签 |
| **目录 / 包结构树** | **` ```text `** | `├──` / `└──` 树；**不要**用 Mermaid |
| **短线性步骤**（≤ ~8 步、无分支） | **` ```text `** | 可用 `→` 链式；也可改成 Mermaid |
| **有分支 / 并行 / 多出口的数据流** | **` ```mermaid `** | 与架构图同一语法 |

**允许的 Mermaid 子集（正式文档）：**

- 推荐：`flowchart TB` / `flowchart LR`（含 `-->`、`---`、`\|label\|`、`{}` 判断节点）
- 可用：`sequenceDiagram`（仅当时序是主叙事）
- **不要**在正式 ARCHITECTURE 里用：`gantt`、`pie`、`gitGraph`、复杂 `classDiagram`（易碎、难审）

**源码可读性（硬性习惯）：**

- 节点标签**短**（一个名字 / 一层包名即可）；**禁止**在标签里堆职责列表或写 `<br/>`
- 图只表达**谁连谁**；职责、文件、方法名放在目录树或图下一二句说明
- 对照好例子：[`tag/docs/ARCHITECTURE.md`](../core/modules/tag/docs/ARCHITECTURE.md) 的架构图——裸源码也能扫出调用关系
- 若一张图在**未渲染**时都扫不动，说明写复杂了，应拆图或改回短标签，而不是把 ASCII 方框原文塞进 Mermaid

**禁止：**

- ❌ 用 `┌─┐` / `└─┘` / `│` 画的 **Unicode 方框图** 表达架构或调用关系（存量迁到 Mermaid）
- ❌ 用 `+---+` 一类 ASCII 边框图表达同上
- ❌ 同一关系既维护一份 ASCII 方框又维护一份 Mermaid（只留 Mermaid）

**官网 / md2html：** Mermaid 围栏原样进入富文本（如 `<pre class="mermaid">`），由前台渲染；目录树与短 `text` 步骤按普通 `<pre>` 输出，不做方框解析。

**存量：** 发现方框图即改为 Mermaid；仅目录树与短步骤的 `text` 可保留。

### `docs/DECISIONS.md`（可选；模板见 [`docs/DECISIONS.md`](doc_templates/module/docs/DECISIONS.md)）

> 设计与决策合一文档——"为什么这么设计、定了什么"。有非平凡设计过程或关键选型时必写；都没有时**省略整文件**。

| 章节 | 必须 / 可选 | 说明 |
|------|------------|------|
| 文首（模块名 + 版本 + 一句话说明） | 必须 | 版本 = `module_info.yaml` |
| 设计目标 | 必须 | 要解决什么——业务目标、性能目标或其他；写清约束与上下文 |
| 方案与思路 | 必须 | 当时有哪些候选方案、怎么比较的、为什么这么走；可引用 ARCHITECTURE 现状，不重复粘贴 |
| 决策点（`## DEC-01:`、`## DEC-02:`…） | 必须 | 每条独立编号，追加在末尾不回头改历史 |

| 每个决策点的固定结构 | 必须 |
|-------------------|------|
| 编号 + 标题 | 如 `## DEC-01: 数据库引擎选择` |
| 是什么 | 一句话决定（选 DuckDB 作为默认引擎） |
| 为什么选它 | 核心理由（多进程 worker 池支持好、列式存储、开箱即用） |
| 放弃了什么 | 列方案 B / C 及放弃理由（Postgres：安装重；MySQL：列式支持差） |
| 影响（可选） | 这个决定带来的约束或后续事项 |

### `docs/USER_GUIDE.md`（必须；模板见 [`docs/USER_GUIDE.md`](doc_templates/module/docs/USER_GUIDE.md)）

> 偏**普通用户**——"这个模块能干嘛、怎么配、常见坑"。与 `QUICKSTART.md`（最短可运行路径）和 `API.md`（调用契约）受众不同。

| 章节 | 必须 / 可选 | 说明 |
|------|------------|------|
| 文首（模块名 + 版本 + 一句话定位） | 必须 | 版本 = `module_info.yaml` |
| 功能总览 | 必须 | 用用户听得懂的话，列能做什么 |
| 配置说明 | 必须 | 配什么、在哪配、默认值 |
| 常见使用方式 | 必须 | 3～5 个常见场景的操作步骤（不贴 API 细节） |
| 常见坑与注意事项 | 可选 | 用户容易踩的雷 |
| 相关文档 | 必须 | README、API.md、ARCHITECTURE.md、glossary.yaml |

### 写作约束

- 中文为主，英文术语可括注；短句，避免营销腔
- **缩写与生僻英文须可读：** 如 `NTQ`（New Tea Quant）、`Facade`（门面：对外统一入口）等，读者未必熟悉。做法二选一或并用：  
  1）**首次出现**用中文释义或括注全称；  
  2）收入本模块 [`glossary.yaml`](doc_templates/module/glossary.yaml)，正文可写「见术语表」。  
  不要在 README 首句堆未解释的英文黑话。
- **README 尽量不出现代码块**；上手代码放 `QUICKSTART`（若有）或 `API.md` 举例；原理放 `CONCEPTS`（若有）
- 非 `API.md` / `docs/DECISIONS.md` 不写历史沿革，只描述当前事实（DECISIONS 每条独立、追加式，天然可追溯）
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

> 模块根 `__test__` 必须维护一份；功能包级可选；**取代** `test_cases.yaml`。  
> 模板：[`__test__/TEST_CASES.md`](doc_templates/module/__test__/TEST_CASES.md)。  
> 测试类型与目录职责见 [CORE 指标 2](../CORE_MODULE_STANDARDS.md)。

**固定结构：** 文首（模块 / **版本：** / 路径）→ Scope → 负责 / 不负责 → 若干 `## Scenario` → 其下 Case 表（函数名 / 文件 / 说明）。

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
| `README.md` | 如何运行、环境/机器假设、指标含义 |
| `CASES.md` | 性能场景与 case；对应 `scripts/` |

---

## 5. 文档检查清单（摘要）

| 检查项 | 说明 |
|--------|------|
| 文档齐全 | 根：README + API + glossary + module_info；docs：ARCHITECTURE + USER_GUIDE；（可选）QUICKSTART / DECISIONS / CONCEPTS |
| 从模板 copy | 章节与 [`doc_templates/module/`](doc_templates/module/) 一致 |
| 版本号一致 | module_info 与各文档文首 `**版本：**` / `# Version:` 一致；`devcli.py p` 闸门 |
| 文档同步 | 与代码一致；触发见 §3 |
| 根目录 `API.md` | 签名 / 状态 / 参数表对齐代码；有 `test_api.py` |
| 无双源 | 无并行 `api.yaml` / `docs/API.md` |
| `TEST_CASES.md` | scenario/case 与 pytest 对齐；无遗留 `test_cases.yaml` |
| DECISIONS 结构 | 含设计目标 + 方案与思路 + DEC 编号决策点；无遗留 `docs/DESIGN.md` |
| 图示 | ARCHITECTURE「架构图」为 Mermaid；无 Unicode/ASCII 方框流程图；目录树用 `text`（§3.1） |

模块创建 / 维护 / 清理的完整清单（含代码与测试）见 [`CORE_MODULE_STANDARDS.md`](../CORE_MODULE_STANDARDS.md)。

---

**参考：**

- [`CORE_MODULE_STANDARDS.md`](../CORE_MODULE_STANDARDS.md) — 模块创建与维护准则
- [`doc_templates/module/`](doc_templates/module/) — 可 copy 骨架
- [`docs/README.md`](README.md) — 仓库文档导航
- 术语表示例：[`core/infra/project_context/glossary.yaml`](../core/infra/project_context/glossary.yaml)
