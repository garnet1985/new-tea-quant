# 策略工作台设置编辑：决策与方案（Draft）

## Context（上下文）

- 目标页面：`strategy-workbench` 下的策略调试页（console/detail）。
- 页面核心诉求：用户修改策略 `settings`，运行回测（枚举 / 价格回测 / 资金模拟），对比不同实验结果。
- 现状：
  - 策略配置来源是 `userspace/strategies/<strategy>/settings.py`。
  - `settings` 里字段有两类：
    - 框架控制字段（`data/sampling/goal/enumerator/fees/price_simulator/capital_simulator/scanner`）
    - 用户自定义字段（`core`）
- 已识别问题：
  - 若所有字段都走通用 dict 编辑器，灵活但 UX 差、校验弱、可解释性差。
  - 若所有字段都走 schema 强模型，`core` 会被强约束，不符合策略作者自由扩展需求。

---

## Decision（决策）

采用**双轨编辑模式**：

1. **非 `core` section：Schema 驱动强模型表单**
   - 前端按固定 schema 渲染字段、控件、校验和帮助文案。
   - 适用于框架可控、字段语义稳定的配置块。

2. **`core` section：Raw dict 编辑（无 schema）**
   - 前端提供通用 Python dict/JSON 输入能力。
   - 支持 Python 风格输入（单引号、`True/False/None`、`#` 注释）并格式化为标准 JSON。
   - 保持策略作者定义参数的自由度，不要求额外声明 UI schema。

3. **编辑生命周期采用三态**
   - `discard`：自然态。用户改动但未应用/未保存，离开或刷新即丢失。
   - `tmp save`（应用到实验）：仅用于当前实验运行，不写入 `settings.py`。
   - `save`：永久保存，覆盖 `userspace/strategies/<strategy>/settings.py`。

4. **保存时自动生成单份备份**
   - 每次 `save` 前，后端生成/覆盖 `settings.py.bak`（仅保留一份最新备份）。
   - 目标：防误操作回滚，不引入多版本备份管理复杂度。

---

## Why（决策理由）

- `core` 是用户域，语义依赖策略实现，框架无法预定义正确字段模型。
- 非 `core` 是框架域，语义稳定、约束明确，强模型表单更可用、可测、可维护。
- 该划分同时满足：
  - 用户体验（常见配置好填）
  - 灵活性（`core` 不受限）
  - 工程可控性（非 `core` 校验前置 + 后端权威校验）

---

## Solution（方案摘要）

### 1) `core` 编辑能力

- 输入区组件化（可复用到策略工作台）
- 支持：
  - 标准 JSON
  - Python dict 风格兼容解析（含注释与 Python 字面量）
- 错误体验：
  - 顶部错误提示
  - 输入框内行列定位
  - 错误上下文高亮
- 成功后自动格式化（标准 JSON），保证结构规整

### 2) 非 `core` 强模型

- 按 section 分组（`goal/enumerator/price_simulator/capital_simulator/...`）
- 字段定义包含：
  - `type`（switch/select/number/text/array/object）
  - `required/default/range/options`
  - `helperText`
- 前端做基础校验，后端做最终权威校验

### 3) 保存策略（约束）

- 保存时保留未知字段（避免配置“洗掉”）
- 保存交互约束：
  - 页面内分离“应用到实验”（临时）与“保存”（永久）语义
  - 点击“保存”时显式提示将覆盖原 `settings.py`
  - 保存前自动生成/覆盖 `settings.py.bak`（单份）
- `settings` 版本判定规则：
  - `settings` 变化即新版本
  - 忽略 `meta` 与 `performance` 变化

### 4) 按钮与行为暴露（UI 约定）

- `discard`：不单独暴露按钮（自然丢弃）
- `应用到实验`：建议放在各可编辑 section 内（或 section 级工具栏）
- `保存`：建议放在页面右上角策略级操作区，明确“永久覆盖”语义
- 运行区应显示“当前运行配置来源”（临时配置 / 已保存配置）

### 5) 三层回测关系与版本缓存

- 三层依赖：
  - `枚举` 是 `价格回测` 与 `资金模拟` 的前置。
  - 若用户直接触发后两层，系统先自动补跑枚举（同一版本上下文）。
- 版本生成：
  - 用户点击“应用到实验”时生成一个 settings snapshot 版本（临时实验版本）。
  - 任意 settings 变化（忽略 `meta/performance`）进入新版本。
- 结果缓存：
  - 版本级缓存 `settings_snapshot`。
  - 步骤级缓存结果 summary（`enum/price/capital` 按需存在，可缺省）。
  - 若某版本未跑某步骤，则该步骤比较时不可选。
- 可恢复性：
  - 即使枚举中间重结果被策略层版本清理（`max_test_versions/max_output_versions`），
    只要 snapshot+summary 在，仍可“回填该版本 settings 并重跑”恢复。

### 6) 版本对比 UX 与生命周期

- 默认下拉只显示最近 10 个版本（按步骤可用性过滤）。
- 第 11 项为“更多版本…”，触发 popup（DataGrid）做分页加载、搜索、过滤、排序。
- 下拉文案采用“版本号 + 关键指标”：
  - 枚举：机会总数等
  - 价格：ROI/胜率等
  - 资金：收益率/回撤等
- 存储策略：
  - 前端仅缓存当前会话 UI 状态（轻量）。
  - 版本元数据与步骤 summary 持久化在后端（避免前端缓存容量与丢失问题）。
  - 会话态可短生命周期；版本历史按后端策略做清理与分页加载。

---

## Non-goals（当前不做）

- 不要求用户维护 `core_schema` 或任何额外 UI 描述文件。
- 不在第一版实现完整树形字段编辑器（`core` 先以 raw 输入为主）。
- 不在第一版引入复杂的可视化 diff/merge 编辑器。

---

## Risks & Mitigations（风险与应对）

- 风险：Python dict 兼容解析存在边界输入差异  
  - 应对：优先 JSON 严格解析，失败再走兼容解析；失败时保留原文并给出定位。

- 风险：非 `core` schema 演进导致前后端不一致  
  - 应对：schema 版本化 + 未知字段保留策略。

- 风险：用户误改导致回测失败  
  - 应对：前端即时校验 + 后端结构化错误返回（字段路径级）。

- 风险：用户误保存导致配置损坏  
  - 应对：每次保存前自动生成单份 `settings.py.bak`，提供快速回滚入口。

- 风险：调参迭代导致版本过多，选择器拥挤且查询变慢  
  - 应对：默认最近 10 条 + “更多版本”分层查询；后端分页与索引化 summary 拉取。

- 风险：用户误以为“清理枚举中间结果”意味着历史版本不可恢复  
  - 应对：在文案与实现上明确“版本历史（snapshot+summary）”与“重结果文件清理”解耦。

---

## Next（后续执行建议）

1. 输出非 `core` 第一批字段 schema（按 section）。
2. 将 `core` 输入组件嵌入策略调试页左栏。
3. 接通后端 validate/save API，统一错误路径回传格式。
4. 设计并实现版本元数据与步骤 summary 的后端持久化模型（含分页接口）。
5. 加入“最近 10 + 更多版本 popup”的对比 UI（按步骤可用性过滤）。

