# 模块文档规范（Module Documentation Standard）

本规范用于统一 NTQ 各模块的文档结构、写作格式与维护规则，作为后续文档整理的执行标准。

---

## 1. 目标与范围

**目标**：
- 让新成员能在 5-10 分钟内理解一个模块做什么、怎么用、改哪里。
- 让维护者能快速定位模块边界、关键决策和 API。
- 降低文档重复、过期和链接失效概率。

**范围**：
- `core/modules/*`
- `core/infra/*`
- `userspace/*`（按轻量规范执行）

---

## 2. 文档放置策略

### 2.1 权威入口

- 仓库对外入口：根目录 `README.md`
- 版本变更入口：根目录 `CHANGELOG.md`

### 2.2 模块文档位置

- 采用**混合方案（默认策略）**：
  - 模块细节文档放在模块目录内的 `docs/` 子目录（就近放置、随代码演进）
  - `docs/` 作为集中导航与跨模块专题目录
- `docs/` 不作为模块实现细节的唯一来源。

示例（含可选的详细设计）：
- `core/modules/strategy/README.md`
- `core/modules/strategy/module_info.yaml`
- `core/modules/strategy/docs/ARCHITECTURE.md`
- `core/modules/strategy/docs/API.md`
- `core/modules/strategy/docs/DECISIONS.md`
- `core/modules/strategy/docs/DESIGN.md`（可选，见 §3.4）

### 2.3 目录职责边界

- 根目录 `README.md`：对外入口、快速开始、最常用命令。
- `docs/README.md`：文档导航中心（目录与链接，不承载模块实现细节）。
- 模块根目录：保留 `README.md` 与 `module_info.yaml`。
- 模块 `docs/`：放置 `ARCHITECTURE.md`、`API.md`、`DECISIONS.md` 等细节文档；若需要详细设计，则使用 `docs/DESIGN.md`（见 §3.4），**不得**在模块根目录另放一份同名设计文档以免双源。
- `docs/` 专题文档：跨模块内容（例如规范、总览、迁移指南、术语）。

### 2.4 迁移与兼容原则

- 现有集中在 `docs/core_modules/*`、`docs/infra/*` 的模块文档，后续逐步迁移到对应模块目录（`README.md` + `module_info.yaml` + `docs/*`）。
- 某模块迁移完成后，删除 `docs/` 下与该模块重复的专题副本（例如已迁至 `core/infra/db/docs/` 的，则删除 `docs/infra/db/*`），并更新 `docs/project_overview.md` 等导航中的链接，避免双源。
- 尚未迁移的模块可仍使用 `docs/infra/<name>/` 等路径；迁移完成即删旧稿。

---

## 3. 模块文档清单（必须/可选）

## 3.1 Core/Infra 主模块（必须）

每个主模块至少包含以下4 份文档：

1. `README.md`（模块入口）
2. `docs/ARCHITECTURE.md`（架构与边界）
3. `docs/API.md`（公开接口）
4. `docs/DECISIONS.md`（关键设计决策）

并且必须包含：

- `module_info.yaml`（模块元信息）

**不要求**每个主模块都有 `docs/DESIGN.md`。体量小、子模块少、行为可由 `ARCHITECTURE.md` 说清的模块可以省略；一旦出现 **`docs/DESIGN.md`**，则必须遵守 **§3.4**。

## 3.2 Userspace 模块（轻量必须）

每个 userspace 模块至少包含：

1. `README.md`
2. `docs/API.md`（若无可调用 API，可用“配置与扩展点说明”替代）
3. `module_info.yaml`

建议有复杂逻辑时补充：
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/DESIGN.md`（若达到 §3.4 的适用条件）

## 3.3 可选文档

- `MIGRATION.md`（破坏性变更迁移指南）
- `FAQ.md`（高频问题）
- `EXAMPLES.md`（模块专属示例）

## 3.4 `docs/DESIGN.md`（可选；有则必规范）

**何时需要**：满足任一条即可考虑新增或保留 `DESIGN.md`（否则用 `ARCHITECTURE.md` 即可）：

- 多个协作子系统或分层，仅用「工作拆分」不足以说明协作方式；
- 非平凡的数据流、并发/队列、生命周期或错误恢复路径；
- 明确的扩展点、插件边界或适配器矩阵（例如多后端、多方言）；
- 与配置、存储格式强耦合且易与实现漂移的细节（类图级说明有助于对齐代码）。

**硬性约定**（只要仓库里存在该模块的设计文档且采用本规范，即适用）：

1. **路径与文件名**：固定为模块内 `docs/DESIGN.md`，不写 `Design.md`、不放模块根目录。
2. **与 ARCHITECTURE 分工**：`ARCHITECTURE.md` 保持 overview + 职责边界 + 工作拆分；**实现向**的类关系、序列/数据流、配置与扩展细节放在 `DESIGN.md`，避免两大段重复；重复处用链接指向另一文档。
3. **交叉链接**：`ARCHITECTURE.md` 的「相关文档」中须包含指向 `DESIGN.md` 的链接；`DESIGN.md` 文首须有返回 `ARCHITECTURE.md` 的链接（及版本与 `module_info.yaml` 中 `version` 一致）。
4. **事实来源**：`DESIGN.md` 以当前代码为准；不写历史沿革段落（沿革放在 `DECISIONS.md`）。
5. **入口曝光**：若存在 `DESIGN.md`，`README.md` 的「相关文档」与「快速定位」目录树中须列出 `docs/DESIGN.md`。

---

## 4. 每份文档固定结构（模板）

## 4.1 `README.md`（模块入口）

固定章节：

1. 模块职责（一句话）
2. 适用场景（2-4 条）
3. 快速开始（最小可运行示例）
4. 目录结构（仅关键文件）
5. 模块依赖（仅列 `module_info.yaml` 中声明的依赖及用途）
6. 相关文档链接（`ARCHITECTURE` / `API` / `DECISIONS`；若存在 `DESIGN` 则一并列出）

## 4.2 `ARCHITECTURE.md`（架构）

固定章节：

1. 模块介绍（1-2 句话，说明该模块做什么）
2. 模块目标（当前版本要完成的能力）
3. 工作拆分（核心子模块/管理器 + 每项 1-2 句职责）
4. 依赖说明（对应 `module_info.yaml` 的依赖及用途）
5. 模块职责与边界（In scope / Out of scope）
6. 架构/流程图
7. 相关文档（链至 `./API.md`、`./DECISIONS.md`；若存在 `docs/DESIGN.md`，须链至 `./DESIGN.md`）

额外约束：

- `ARCHITECTURE.md` 为当前版本的架构总览（overview），内容保持极简。
- 文档中的版本号必须与 `module_info.yaml` 的 `version` 一致。
- 默认不写示例代码，除非没有示例就无法说明关键流程。

## 4.3 `API.md`（接口）

**版式（必须一致，全仓库统一）**

文首用一两句说明：本模块 API 采用统一条目格式（可与 `core/infra/db/docs/API.md` 对齐）。

按**类型或职责**分节（`## DatabaseManager`、`## ClassDiscovery` 等）。每个对外入口单独一块，结构固定为：

1. 小节标题固定为 **`### 函数名`**（字面三个字，不用反引号包裹）。
2. 下一行：反引号包住的**完整签名**（含参数默认值与返回注解，与代码一致）。
3. 无序列表，键名固定（冒号为半角 `:`）：
   - `状态：` `stable` / `beta` / `deprecated`
   - `描述：` 一句话职责；必要时补一句边界或语义注意点
   - `诞生版本：` 与 `module_info.yaml` 的 `version` 对齐（新接口写引入时的模块版本）
   - `params：` 无参数时写 `params：无`。有参数时使用 **Markdown 表格**，列为 **`名字` | `类型` | `说明`**（表头第二行用 `|------|------|------|` 分隔）。**可选参数**在「名字」列用 `` `参数名` (可选) `` 标明（与签名中默认值对应）；「说明」列写语义、默认值或约束，避免仅用「可选」二字敷衍。
   - `返回值：` 类型与语义；无返回值写 `None`
4. 可选：`错误与异常：`（仅当调用方需要处理或文档必须提示时）

表格与 `- 返回值：` 之间空一行。

**数据类 / 仅类型无方法**：同样使用 `### 函数名` + 签名行（可写类型名或合成构造函数签名），字段用同一套三列表格，与 `DiscoveryResult`、`DiscoveryConfig` 等现有文档一致。

**示例（代码）**

- 简单 CRUD 式 API：条目内可不附示例，依赖 `README` 快速开始即可。
- **配置对象 + 多参数、回调、或易混语义**（如发现规则、连接串、批量选项）：应在文档中给出示例，任选其一：
  - 在该条目的列表末尾增加 **`- 示例：`**，下面接缩进代码块；或
  - 在 `API.md` 文末增加 **`## 示例`**，集中放 1～2 段最小可运行代码（风格见 `core/infra/db/docs/API.md` 文末）。

示例代码须与当前实现一致；需要占位处用注释标明（如「将 `BaseX` 换为项目基类」）。

仅记录「用户或外部模块需要主动调用」的接口；内部私有方法不写入。

## 4.4 `DECISIONS.md`（决策）

每条决策统一格式：

1. 背景（Context）
2. 决策（Decision）
3. 理由（Rationale）
4. 影响（Consequences）
5. 备选方案（Alternatives，可选）

建议命名：`决策 N：<标题>`，并按时间追加，不覆盖历史。

## 4.5 `DESIGN.md`（详细设计，可选）

仅当模块包含 `docs/DESIGN.md` 时使用本节结构；清单与硬性约定见 **§3.4**。

建议文首固定块：

1. 标题与**版本**（与 `module_info.yaml` 的 `version` 一致）
2. 一句话说明本文档覆盖范围
3. **相关文档**：模块内 `docs/ARCHITECTURE.md`（必须）

正文可按模块需要组织，常见章节包括：核心类型与职责、关键数据流/时序、配置与方言差异、扩展点与约束、与边界外系统的交互示意。保持与代码一致，大段说明避免与 `ARCHITECTURE.md` 重复。

## 4.6 `module_info.yaml`（模块信息）

固定字段（键名简短，不加 `module_` 前缀）：

- `name`：机器名（示例：`infra.db`）
- `version`：模块版本（当前统一从 `0.2.0` 起步）
- `compatible_core_versions`：兼容的 core 版本范围（semver range，示例：`>=0.2.0`）
- `description`：模块简述
- `dependencies`：模块依赖列表（模块级粒度）

版本规则：

- 所有模块的初始 `version` 统一为 `0.2.0`。
- 所有模块的初始 `compatible_core_versions` 统一为 `>=0.2.0`。
- 当模块逻辑变更并依赖更高版本 core 能力时，必须同步提高 `compatible_core_versions` 的最低版本。

建议可选字段（为未来模块生态预留）：

- `status`：`stable` / `beta` / `experimental` / `deprecated`
- `entry`：模块入口（如 `python_path` 或脚本路径）

---

## 5. 写作风格与格式约束

- 中文为主，英文术语可括注。
- 使用短句，避免营销性描述。
- 示例代码必须可复制运行，优先使用 `start-cli.py` 相关命令。
- 所有相对链接必须可在仓库内直接打开。
- 避免在多个文档重复大段内容：重复信息用链接替代。
- 非 `API.md` / `DECISIONS.md` 文档不写历史沿革，只描述当前事实。

---

## 6. 文档维护触发规则

满足任一条件时，必须同步更新对应模块文档：

- 公共 API 变更（新增、删除、参数变化）
- 模块职责边界变化
- 关键流程变化（执行链路、数据流、存储结构）
- 配置结构变化（字段、默认值、语义）

发布前最低检查：

1. 根目录 `README.md`
2. 根目录 `CHANGELOG.md`
3. 涉及改动模块的文档（按本规范）

---

## 7. 文档健康检查清单（PR 自检）

- [ ] 模块文档是否齐全（按模块级别）
- [ ] `README.md` 是否提供最小可运行示例
- [ ] `API.md` 中签名是否与代码一致，且条目结构符合 §4.3（`### 函数名`、`params` 三列表格、可选参数标 `(可选)`）
- [ ] 复杂或易混 API 是否在 `API.md` 条目或 `## 示例` 中有最小示例（与实现一致）
- [ ] `ARCHITECTURE.md` 的职责边界是否仍成立
- [ ] `DECISIONS.md` 是否记录了新的关键取舍
- [ ] 若存在 `docs/DESIGN.md`：路径是否为 `docs/DESIGN.md`，`ARCHITECTURE` / `DESIGN` / `README` 是否互相链上，内容是否仍与代码一致
- [ ] 所有链接可用、命令可执行

---

## 8. 落地顺序建议

1. 先补齐缺失文件（空壳模板也可）
2. 再统一目录与命名（`README/ARCHITECTURE/API/DECISIONS`，按需 `DESIGN`）
3. 最后做内容深度整理（避免一开始大改导致反复返工）

---

**备注**：本规范不覆盖 `docs/development/`，该目录按内部工作文档管理。
