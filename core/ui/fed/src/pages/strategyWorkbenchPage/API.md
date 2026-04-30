# Strategy Workbench — BFF API 归纳（策略工作台）

本文档描述 **策略工作台** 前端与 **BFF** 之间的接口约定。所有交互经 BFF，禁止 FED 直连其它后端。**仅收录当前已约定的契约**；未落地的端点不写入本文。

## 术语与命名（统一口径）

| 用语 | 说明 |
|------|------|
| **策略工作台** / **Strategy Workbench** | 本产品能力：策略列表 + 单策略调试（左侧配置、中间执行、右侧报告）。**本模块与代码、路由统一用此称呼。** |
| URL 前缀 | 列表与调试页路由为 **`/strategy-workbench`**（保持不变）。 |
| 弃用别名 | 不再使用 **console**、**workspace** 指代本模块；历史若出现，逐步替换为 **workbench**。 |

React 路由组件、页面目录名：`strategyWorkbenchPage`、`StrategyWorkbenchPage`。

---

## 全局约定

- **Base path**：`/api/v1`（见 `src/api/conf/apiConfig.js`）。
- **传输格式**：JSON；与 `requestJson` 的通用包装一致。
- **策略标识**：列表项的 **`key`** 与 `userspace/strategies/<key>/` 目录名一致。

### 统一响应与错误（FED `requestJson`）

- 成功：HTTP 2xx 且 JSON 根级 `status === "ok"`。
- 失败：HTTP 非 2xx 或 `status !== "ok"` 时，前端抛错，错误文案优先取 `message.detail`（字符串）。
- BFF 出错：`{"status":"error","message":{"detail":"<人类可读说明>"}}`，HTTP 状态与错误语义一致。

---

## API Contract（策略工作台 · BFF 接口契约）

### 页面框架上下文（供协作快速接手）

`StrategyWorkbenchPage` 可按业务生命周期理解为三段：

1. **修改 settings（preprocess）**
   - 对应执行 job 前的参数准备、校验、临时保存与版本对比。
2. **执行三步（simulation）**
   - UI 中的三个执行步骤，对应后端 simulation 主流程与进度状态。
3. **report（post process / report）**
   - 对应结果整理、报表指标、样本明细、对比展示。

在这三段之上，存在一个贯穿全页的 **snapshot** 概念，用于记录：

- 用户 workbench 状态（当前页上下文、选中的版本、执行态等）。
- 当前工作上下文的版本指针（例如当前配置版本、上次运行版本）。

页面加载时的推荐顺序：

1. 先读取当前策略的 snapshot（恢复用户上次工作台状态）。
2. 再按 snapshot 引用加载 settings / cache / report 所需数据。
3. 最后加载 options/profile（select 候选值与字段联动规则）。

> 当前实现中的持久化承载可先复用现有缓存机制；是否从 `sys_cache` 迁移到专用表（如 snapshot 专表）后续再定。

### API 分层（全局视图）

| 分层 | 目的 | 典型数据 |
|------|------|----------|
| 调度层（Snapshot / Session） | 恢复页面上下文、保存工作台状态、管理版本指针 | snapshot、last_opened_state、compare_targets |
| 数据层（Settings / Cache / Report Data） | 提供实例值与执行中间结果 | settings、run cache、report payload |
| 执行层（Simulation Orchestration） | 启动/跟踪三步执行流程 | run request、step status、progress |
| 选项层（Options / Profiles） | 提供候选值与字段联动规则 | `options`、`profiles` |

### 关键边界约定

- **settings 是实例值真源**：策略配置以整包 settings 为主，不由 options 接口反向生成。
- **options/profile 是候选值真源**：用于约束与渲染可选项，不能替代 settings 当前值。
- **snapshot 是工作台态真源**：用于恢复 UI 工作现场，不替代 settings/report 的业务真源。
- **执行态需可追溯**：启动 simulation 时应冻结本次执行所依赖的版本上下文（便于 report 解释与复现）。

---

本節为**正式契约**：方法、路径、请求/响应形状、消费方与 BFF 职责。新端点按 **SWB-02、SWB-03…** 递增编号后追加；**SWB** = *Strategy Workbench*。

### 契约原则（当前版本）

1. **整包 settings 优先**：单策略调试页以整包读取/整包保存为主链路，便于整体调试与 breaking change 感知。
2. **前端自拆分**：左侧各 block 由 FED 从整包 settings 解析，不要求后端按 block 拆分返回。
3. **主数据与选项并行必需**：SWB-04/05 返回实例值（当前 settings）；SWB-02/03 返回候选值与字段 profile（possible values）。两类契约缺一不可。

### 契约目录

| 编号 | 方法 | 路径 | 摘要 |
|------|------|------|------|
| **SWB-01** | `GET` | `/api/v1/strategies` | 返回已发现策略列表及 meta |
| **SWB-04** | `GET` | `/api/v1/strategies/{strategy_name}/settings` | 读取单策略完整 settings（主链路） |
| **SWB-05** | `PUT` | `/api/v1/strategies/{strategy_name}/settings` | 保存单策略完整 settings（主链路） |
| **SWB-02** | `GET` | `/api/v1/strategies/settings-options/allocation-modes` | 资金分配策略 `capital_simulator.allocation.mode` 下拉选项 |
| **SWB-03** | `GET` | `/api/v1/strategies/settings-options/sampling-strategies` | 采样策略 `sampling.strategy` 下拉选项 |
| **SWB-06** | `POST` | `/api/v1/strategies/{strategy_name}/runs` | 启动执行（枚举/价格/资金），返回 `run_id` |
| **SWB-07** | `GET` | `/api/v1/strategies/{strategy_name}/runs/{run_id}` | 读取执行状态与步骤进度（轮询） |
| **SWB-08** | `POST` | `/api/v1/strategies/{strategy_name}/runs/{run_id}/cancel` | 取消执行 |
| **SWB-09** | `GET` | `/api/v1/strategies/{strategy_name}/run-results/{run_id}` | 读取执行面板摘要结果（enum/price/capital） |
| **SWB-10** | `GET` | `/api/v1/strategies/{strategy_name}/compare-options` | 执行/报告「对比版本」下拉选项 |
| **SWB-11** | `GET` | `/api/v1/strategies/{strategy_name}/reports/{run_id}` | 读取报告面板三类报告摘要（enum/price/capital） |
| **SWB-12** | `GET` | `/api/v1/strategies/{strategy_name}/reports/{run_id}/stocks` | 读取报告样本股票表（支持 report_type） |
| **SWB-13** | `GET` | `/api/v1/strategies/{strategy_name}/reports/{run_id}/stocks/{stock_id}/kline` | 读取单股票 K 线与买卖点明细 |
| **SWB-14** | `GET` | `/api/v1/strategies/{strategy_name}/reports/compare` | 读取本次与对比版本报告数据（双栏对比） |
| **SWB-15** | `GET` | `/api/v1/strategies/{strategy_name}/snapshot` | 读取工作台 snapshot（页面恢复入口） |
| **SWB-16** | `PUT` | `/api/v1/strategies/{strategy_name}/snapshot` | 保存工作台 snapshot（UI态 + 指针） |
| **SWB-17** | `GET` | `/api/v1/strategies/{strategy_name}/versions` | 读取配置版本列表（对比/恢复来源） |
| **SWB-18** | `GET` | `/api/v1/strategies/{strategy_name}/versions/{version_id}` | 读取单个配置版本详情 |
| **SWB-19** | `POST` | `/api/v1/strategies/{strategy_name}/versions/{version_id}/restore` | 恢复指定版本到当前 settings |
| **SWB-20** | `POST` | `/api/v1/strategies/{strategy_name}/versions` | 固化当前工作台配置为后端版本（供应用/对比） |

---

### 单策略调试页 · 左侧设置（`StrategySettingsPanel`）

左侧折叠块对应整包 **`settings`**（与各策略 `settings.py` 载入结构一致）。其中 **下拉枚举**不硬编码在前端可读配置中维持与 Python 校验一致；由 **SWB-02 / SWB-03** 提供 **`value` + `label`** 列表。

| UI 折叠块 | `settings` 键 | 枚举类 API |
|-----------|----------------|------------|
| 策略基本信息 | `meta`、`data` | — |
| 策略核心设置 | `core` | — |
| 策略目标设置 | `goal` | — |
| 全局费用设置 | `fees` | — |
| 机会枚举参数 | `enumerator` | — |
| 价格回测参数（含时间段） | `price_simulator` | — |
| 资金模拟参数（含时间段） | `capital_simulator`（Python 模块亦写作 capital_allocation 语义） | **SWB-02**（`allocation.mode`） |
| 采样配置 | `sampling` | **SWB-03**（`strategy`） |

整包 settings 读写（SWB-04 / SWB-05）与选项/profile（SWB-02 / SWB-03）并行必需：前者给“当前值”，后者给“可选值与联动规则”。

---

### SWB-04 — 读取单策略完整 settings（主链路）

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/settings`
- **消费页面**：`StrategyWorkbenchPage`（路由 `/strategy-workbench/:strategyName`）
- **语义**：返回该策略当前生效的整包 settings。FED 在本地拆分到左侧各 block。

#### 请求契约

- **Path params**：
  - `strategy_name`（string，必填）：策略目录名，对应 `userspace/strategies/{strategy_name}`。
- Query：无。
- Body：无。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "strategy_name": "example",
    "settings": {
      "meta": { "name": "example", "description": "", "is_enabled": true },
      "core": {},
      "data": {},
      "goal": {},
      "fees": {},
      "enumerator": {},
      "price_simulator": {},
      "capital_simulator": {},
      "sampling": {},
      "scanner": {}
    }
  }
}
```

#### `message.settings` 约定

- 类型：`object`（完整 settings）。
- 要求：保持与策略目录下 `settings.py` 语义一致；未知键可透传，不做静默丢弃。
- FED 处理：不依赖后端分段字段，按自身 schema 自行读取/拆分。

#### 响应契约（失败）

- 404：策略不存在。
- 500：读取/解析失败。
- 统一错误体：`{ "status": "error", "message": { "detail": "..." } }`。

#### BFF / Backend 职责

1. 按 `strategy_name` 定位策略目录并读取 settings。
2. 将 Python 配置结构稳定序列化为 JSON 对象返回（不做 UI 专属拆分）。
3. 错误时返回可读 `message.detail`，便于 FED 直接提示。

---

### SWB-05 — 保存单策略完整 settings（主链路）

- **Method & path**：`PUT /api/v1/strategies/{strategy_name}/settings`
- **消费页面**：`StrategyWorkbenchPage`（保存配置动作）
- **语义**：FED 提交完整 settings，BFF 校验并写回策略 `settings.py`（或等价存储）。

#### 请求契约

- **Path params**：
  - `strategy_name`（string，必填）
- **Body**：

```json
{
  "settings": {
    "meta": { "name": "example", "description": "", "is_enabled": true },
    "core": {},
    "data": {},
    "goal": {},
    "fees": {},
    "enumerator": {},
    "price_simulator": {},
    "capital_simulator": {},
    "sampling": {},
    "scanner": {}
  }
}
```

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "strategy_name": "example",
    "saved": true
  }
}
```

#### 响应契约（失败）

- 400：请求体非法（`settings` 缺失或类型错误）。
- 422：settings 校验不通过（建议在 `message` 返回可读错误详情）。
- 500：写入失败。
- 统一错误体：`{ "status": "error", "message": { "detail": "..." } }`。

#### BFF / Backend 职责

1. 校验请求体结构，确保是完整 settings 对象。
2. 调用策略 settings 校验逻辑（与后端运行时一致）。
3. 原子写回并返回保存结果；失败时不部分落盘。
4. 建议在保存成功后自动创建一个 `source=save` 的配置版本（等同 SWB-20 语义），保证后续可对比/可恢复。

---

### 执行面板（`StrategyExecutionPanel`）契约设计

UI 当前行为要点（来自 `strategyExecutionPanel.js`）：

- 三步：`enum`、`price`、`capital`。
- 依赖：当 `enum` 不是 `done` 时，点击 `price/capital` 会先补跑 `enum`。
- 执行中：显示单步 progress，禁止再次触发。
- 对比：每一步完成后可选「对比版本」展示摘要。

后端契约按「启动一次 run -> 轮询 run 状态 -> 读取摘要结果」设计。

---

### SWB-06 — 启动执行 run

- **Method & path**：`POST /api/v1/strategies/{strategy_name}/runs`
- **语义**：启动一次执行任务；可指定目标步骤。若目标是 `price/capital` 且枚举结果不可用，后端按依赖自动补跑。

#### 请求契约

Path params:
- `strategy_name`（string，必填）

Body:

```json
{
  "target_step": "price",
  "settings_version": "v_current",
  "settings_snapshot": {},
  "idempotency_key": "optional-client-uuid"
}
```

字段说明：
- `target_step`：`enum | price | capital`（必填）
- `settings_version`：可选，指向已保存版本（推荐）
- `settings_snapshot`：可选，未保存时可传冻结副本（与 snapshot 体系配合）
- 两者至少提供其一，便于结果可追溯。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "run_id": "run_20260428_001",
    "strategy_name": "example",
    "state": "running",
    "target_step": "price",
    "resolved_chain": ["enum", "price"]
  }
}
```

---

### SWB-07 — 轮询 run 状态

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/runs/{run_id}`
- **语义**：返回当前 run 生命周期状态与步骤进度；执行面板轮询此接口。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "run_id": "run_20260428_001",
    "state": "running",
    "running_step": "enum",
    "progress_pct": 42,
    "step_status": {
      "enum": "running",
      "price": "idle",
      "capital": "idle"
    },
    "updated_at": "2026-04-28T03:00:00Z"
  }
}
```

状态值约定：
- run `state`: `queued | running | done | failed | cancelled`
- step status: `idle | running | done | failed | cancelled`

---

### SWB-08 — 取消 run

- **Method & path**：`POST /api/v1/strategies/{strategy_name}/runs/{run_id}/cancel`
- **语义**：请求取消正在运行的任务。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "run_id": "run_20260428_001",
    "cancelled": true
  }
}
```

---

### SWB-09 — 读取执行摘要结果

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/run-results/{run_id}`
- **语义**：run 完成后读取执行面板摘要（对应 UI 三行摘要）。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "run_id": "run_20260428_001",
    "result": {
      "enum": { "opportunities": 123 },
      "price": { "winRate": 56.2, "roi": 18.4, "avgHoldDays": 13.1 },
      "capital": { "initialCapital": 1000000, "endCapital": 1031800, "profit": 31800, "retPct": 3.18 }
    }
  }
}
```

说明：
- 未执行到的步骤可为 `null`。
- 若重新跑 `enum`，后端应使下游旧摘要失效（与当前 UI 逻辑一致）。

---

### SWB-10 — 对比版本选项

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/compare-options`
- **语义**：返回执行面板/报告共用的对比版本下拉列表（替换前端 mock `STRATEGY_WORKBENCH_COMPARE_VERSION_OPTIONS`）。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "versions": ["latest", "v3", "v2", "v1"]
  }
}
```

---

### 报告面板（`StrategyReportPanel`）契约设计

UI 当前行为要点（来自 `strategyReportPanel.js` 与三个 report 子组件）：

- 报告分三类：`enum` / `price` / `capital`，仅在对应执行步骤 `done` 后展示 Tab。
- 报告弹窗支持“本次结果 vs 对比版本结果”双栏对比。
- 每类报告包含：汇总指标 + 样本股票表（最多10）；
  其中价格报告支持点击样本股票打开 K 线弹窗（买卖点示意）。

实现策略（当前阶段）：

- **UI-first contract**：先以当前前端 UI 所需字段/结构定义契约，优先保证前后端联调与页面可用。
- **后端渐进增强**：summary 的计算口径、存储结构、聚合性能与可追溯性后续迭代增强，不阻塞本轮契约冻结。

后端契约按「报告主数据 + 样本明细 + 单股详情 + 对比聚合」拆分。

---

### SWB-11 — 读取报告主数据（三类摘要）

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/reports/{run_id}`
- **语义**：返回报告面板所需的三类摘要指标，供 Tab 内容渲染。

#### 请求契约

Path params:
- `strategy_name`（string，必填）
- `run_id`（string，必填）

Query（可选）：
- `report_types=enum,price,capital`（不传则默认全量）

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "run_id": "run_20260428_001",
    "reports": {
      "enum": {},
      "price": {},
      "capital": {}
    },
    "available_tabs": ["enum", "price", "capital"]
  }
}
```

说明：
- `reports.<type>` 结构由各报告模块定义（指标字段可演进，保持向后兼容优先）。
- `available_tabs` 与执行完成状态对齐，前端据此决定可见 Tab。

---

### SWB-12 — 读取报告样本股票表

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/reports/{run_id}/stocks`
- **语义**：返回某报告类型样本股票数据，供 `ReportStockSampleGrid`。

#### 请求契约

Path params:
- `strategy_name`（string，必填）
- `run_id`（string，必填）

Query:
- `report_type`（必填）：`enum | price | capital`
- `limit`（可选，默认10）
- `search`（可选，按代码/名称过滤）
- `sort_by`（可选，report_type 相关字段）
- `sort_order`（可选，`asc | desc`）

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "report_type": "price",
    "rows": [
      {
        "stock_id": "600519.SH",
        "stock_name": "贵州茅台",
        "win_rate": 58.3,
        "roi": 12.6,
        "hold_days": 14.2
      }
    ],
    "total": 1
  }
}
```

说明：
- 字段按 `report_type` 变化；上例为 `price`。
- `stock_id` 为后续 K 线详情接口主键（SWB-13）。

---

### SWB-13 — 读取单股票 K 线与买卖点

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/reports/{run_id}/stocks/{stock_id}/kline`
- **语义**：返回价格报告中 K 线弹窗的数据（OHLC + 交易标记）。

#### 请求契约

Path params:
- `strategy_name`（string，必填）
- `run_id`（string，必填）
- `stock_id`（string，必填）

Query（可选）：
- `start_date` / `end_date`（不传则使用 run 对应窗口）

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "stock_id": "600519.SH",
    "stock_name": "贵州茅台",
    "candles": [
      { "date": "2026-01-01", "open": 100.1, "high": 101.2, "low": 99.8, "close": 100.9 }
    ],
    "markers": [
      { "type": "buy", "date": "2026-01-09", "price": 103.2 },
      { "type": "sell", "date": "2026-01-31", "price": 109.8 }
    ]
  }
}
```

---

### SWB-14 — 报告对比数据（双栏）

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/reports/compare`
- **语义**：返回本次 run 与对比版本（或 run）同口径报告数据，供“对比结果”弹窗双栏展示。

#### 请求契约

Path params:
- `strategy_name`（string，必填）

Query:
- `base_run_id`（必填）
- `compare_version`（必填，值来自 SWB-10）
- `report_type`（可选：`enum | price | capital`，不传返回三类）

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "base_run_id": "run_20260428_001",
    "compare_version": "v3",
    "report_type": "price",
    "base_report": {},
    "compare_report": {}
  }
}
```

说明：
- `base_report/compare_report` 字段结构与 SWB-11 对应 `report_type` 一致。
- 若对比目标不存在，返回统一错误体（建议 404/422）。

---

### SWB-01 — 获取已发现策略列表

- **Method & path**：`GET /api/v1/strategies`
- **消费页面**：`StrategyListPage`（路由 `/strategy-workbench`）
- **FED 调用**：`fetchStrategyList()`（`src/api/apis/strategyApi.js`）

**场景说明**：进入列表时与「刷新」时各请求 **SWB-01** 一次。双击行进入 `/strategy-workbench/:strategyName`。

#### 策略列表页：搜索与分页（FED 行为，与 BFF 无附加参数）

页面 `StrategyListPage` 上提供 **按策略名搜索** 与 **表格分页**；二者均在**取得 SWB-01 全量列表后**在浏览器内完成，**不**向 BFF 传 `q` / `page` / `page_size` 等参数，也**不**因翻页或输入搜索词而再次请求列表。

| 能力 | FED 实现要点 |
|------|----------------|
| **搜索** | 文本框绑定 `nameQuery`。对 **`name`** 字段做 **不区分大小写的子串匹配**（`trim` 后为空则显示全部）。搜索结果来自内存中的 `rows`，非服务端筛选。切换搜索关键词时 **页码重置为第 1 页**（`page` → `0`）。 |
| **分页** | MUI DataGrid：`paginationModel`（`page`、`pageSize`）；**`pageSizeOptions` 固定为 `[10]`**（每页 10 条）。分页作用在 **`displayRows`**（先按搜索过滤后的数据集）上，属客户端分页。 |

补充：**「刷新」**按钮仅重新执行 **SWB-01**，与搜索词、当前页无关（重新拉取后仍以当前搜索词过滤、分页状态沿用 DataGrid 惯例）。

#### 请求契约

无 Query；无 Body。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "strategies": [
      {
        "key": "example",
        "name": "Example display name",
        "description": "",
        "is_enabled": true
      }
    ]
  }
}
```

**`message.strategies[]` 字段**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `key` | string | 是 | 策略目录名；BFF 按 `key` 升序排序。 |
| `name` | string | 是 | **meta.name**；缺省时 BFF 用目录名兜底。 |
| `description` | string | 否 | **meta.description**，可为空串。 |
| `is_enabled` | boolean | 是 | **meta.is_enabled**。 |

#### FED 归一化类型（表格行）

```ts
type StrategyListRow = {
  id: string;           // = key（目录名），DataGrid row id
  name: string;         // 展示名，来自 meta.name
  description: string;
  is_enabled: boolean;
};

type FetchStrategyListResult = {
  data: StrategyListRow[];
};
```

**映射规则**：`id = key || name`；`name = name || key`；`description` 默认 `''`；`is_enabled` → `Boolean(...)`。

#### 响应契约（失败）

HTTP 500（或与错误语义一致的 4xx/5xx），示例：

```json
{
  "status": "error",
  "message": {
    "detail": "获取策略列表失败: <异常信息>"
  }
}
```

#### BFF / Backend 职责

1. `StrategyDiscoveryHelper.discover_strategies()` 发现策略并遍历。
2. 每项：`key` = 目录名；`name` / `description` / `is_enabled` 来自 `StrategyInfo.settings.meta`（与当前 `core/ui/bff/APIs/strategy_workbench/service.py` 一致）。
3. 按 `key` 升序排序。
4. 异常时返回 `status: error`、`message.detail`，HTTP 500。

---

### SWB-02 — 资金分配模式选项（必需选项契约）

- **Method & path**：`GET /api/v1/strategies/settings-options/allocation-modes`
- **绑定字段**：`capital_simulator.allocation.mode`（见 `strategyCapitalSimulator` schema）
- **FED 调用**：`fetchCapitalAllocationModeOptions()`（`strategyApi.js`）

**语义**：返回可选 **`value`** 必须与 ``core.modules.strategy.engines.simulator.capital_allocation.data_classes.settings`` 中 **mode** 校验集合一致（当前为 `equal_capital` / `equal_shares` / `kelly` / `custom`）。**`label`** 为界面展示文案。并返回每个 mode 对应的字段 profile，供前端在切换 mode 时联动显示/校验下方字段。

#### 请求契约

无 Query；无 Body。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "options": [
      { "value": "equal_capital", "label": "每个机会均等资金买入" },
      { "value": "equal_shares", "label": "每个机会均等股数买入" },
      { "value": "kelly", "label": "凯莉公式" },
      { "value": "custom", "label": "自定义" }
    ],
    "profiles": {
      "equal_capital": {
        "configurable_fields": ["allocation.max_portfolio_size", "allocation.max_weight_per_stock"],
        "required_fields": []
      },
      "equal_shares": {
        "configurable_fields": [
          "allocation.max_portfolio_size",
          "allocation.max_weight_per_stock",
          "allocation.lot_size",
          "allocation.lots_per_trade"
        ],
        "required_fields": ["allocation.lot_size", "allocation.lots_per_trade"]
      },
      "kelly": {
        "configurable_fields": [
          "allocation.max_portfolio_size",
          "allocation.max_weight_per_stock",
          "allocation.kelly_fraction"
        ],
        "required_fields": ["allocation.kelly_fraction"]
      },
      "custom": {
        "configurable_fields": ["allocation.max_portfolio_size", "allocation.max_weight_per_stock"],
        "required_fields": []
      }
    }
  }
}
```

**`message.options[]`**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `value` | string | 是 | 写入 `settings` 的机器值 |
| `label` | string | 是 | 下拉展示文案 |

**`message.profiles`**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `profiles.<mode>.configurable_fields` | string[] | 是 | 当前 mode 可编辑字段（点路径）。前端可用于字段显隐。 |
| `profiles.<mode>.required_fields` | string[] | 是 | 当前 mode 必填字段（点路径）。前端可用于即时校验提示。 |

#### 响应契约（失败）

与 SWB-01 相同形态：`status: error`，`message.detail`。

#### BFF / Backend 职责

1. 选项中的 **`value`** 集合与框架 **capital_simulator allocation mode** 校验逻辑对齐（不可擅自增加未在后端注册的 mode）。
2. **`label`** 由 BFF 维护中文文案；若框架新增合法 `value`，BFF 须在有序列表或兜底分支中给出对应项。
3. 维护 `profiles`，确保 mode 切换后的字段联动与后端能力一致。

---

### SWB-03 — 采样策略选项（必需选项契约）

- **Method & path**：`GET /api/v1/strategies/settings-options/sampling-strategies`
- **绑定字段**：`sampling.strategy`（见 `strategySampling` schema）
- **FED 调用**：`fetchSamplingStrategyOptions()`（`strategyApi.js`）

**语义**：返回可选 **`value`** 必须与 ``StrategySamplingSettings`` / ``KNOWN_STRATEGIES`` 一致（当前含 `continuous`、`uniform`、`stratified`、`random`、`pool`、`blacklist`）。并返回每个 strategy 对应的字段 profile，供前端联动展示对应子配置。

#### 请求契约

无 Query；无 Body。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "options": [
      { "value": "continuous", "label": "连续采样（默认）" },
      { "value": "uniform", "label": "均匀采样" },
      { "value": "stratified", "label": "分层采样" },
      { "value": "random", "label": "随机采样" },
      { "value": "pool", "label": "指定股票池采样" },
      { "value": "blacklist", "label": "排除黑名单采样" }
    ],
    "profiles": {
      "continuous": {
        "configurable_fields": ["sampling.sampling_amount", "sampling.continuous.start_idx"],
        "required_fields": []
      },
      "uniform": {
        "configurable_fields": ["sampling.sampling_amount"],
        "required_fields": []
      },
      "stratified": {
        "configurable_fields": ["sampling.sampling_amount", "sampling.stratified.seed"],
        "required_fields": []
      },
      "random": {
        "configurable_fields": ["sampling.sampling_amount", "sampling.random.seed"],
        "required_fields": []
      },
      "pool": {
        "configurable_fields": ["sampling.sampling_amount", "sampling.pool.stock_ids", "sampling.pool.file"],
        "required_fields": []
      },
      "blacklist": {
        "configurable_fields": ["sampling.sampling_amount", "sampling.blacklist.stock_ids", "sampling.blacklist.file"],
        "required_fields": []
      }
    }
  }
}
```

**`message.options[]`**：字段表同 SWB-02。  
**`message.profiles`**：字段表同 SWB-02。

#### 响应契约（失败）

与 SWB-01 相同形态。

#### BFF / Backend 职责

1. **`value`** 集合与 ``sampling_settings.KNOWN_STRATEGIES`` 对齐。
2. **`label`** 由 BFF 维护；新增合法采样策略时同步扩展列表。
3. 维护 `profiles`，确保 sampling.strategy 切换后子字段联动一致。

---

### Snapshot（工作台状态）契约与存储

决策：**使用专门表承载工作台 snapshot，不复用 `sys_cache`**。

全局概念定义（统一语义）：
- **Draft（前端草稿）**：用户仅在左侧改了 settings，但尚未触发任何后端交互（未执行任一步、未点击保存配置）。只存在于前端内存态，不入库。
- **Version（后端版本）**：一旦发生后端交互即生成/更新的可追溯状态（例如执行任一步写入系统缓存，或点击保存覆盖 settings 文件）。
- **Snapshot（工作台态）**：页面 UI 上下文与“当前使用哪个版本”的指针；不替代 settings 真源。

原因：
- snapshot 是业务对象（可演进 schema + 语义稳定），不是临时缓存；
- 需要版本化、并发控制与可追溯（`updated_at`、`revision`、操作者）；
- 与执行 run-state、配置版本存在明确关联，后续可做治理与迁移。

---

### SWB-15 — 读取 snapshot（页面加载第一入口）

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/snapshot`
- **语义**：恢复用户上次工作台状态；不存在时返回默认结构。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "strategy_name": "example",
    "snapshot": {
      "snapshot_id": "swb_example_default_user",
      "revision": 7,
      "ui_state": {
        "active_report_tab": "price",
        "expanded_panels": ["settings", "execution", "report"],
        "compare_version": { "enum": "v3", "price": "", "capital": "" }
      },
      "working_state": {
        "current_settings_version": "ver_20260428_003",
        "current_run_id": "run_20260428_001",
        "last_completed_run_id": "run_20260427_003"
      },
      "updated_at": "2026-04-28T03:00:00Z"
    }
  }
}
```

---

### SWB-16 — 保存 snapshot（upsert）

- **Method & path**：`PUT /api/v1/strategies/{strategy_name}/snapshot`
- **语义**：保存页面 UI 态与工作态指针。支持并发控制（`revision`）。

#### 请求契约

```json
{
  "revision": 7,
  "snapshot": {
    "ui_state": {},
    "working_state": {}
  }
}
```

并发建议：
- 若 `revision` 过期，返回 `409 conflict`，前端提示刷新后重试。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "strategy_name": "example",
    "saved": true,
    "revision": 8,
    "updated_at": "2026-04-28T03:01:20Z"
  }
}
```

---

### SWB-17 — 读取配置版本列表

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/versions`
- **语义**：返回可对比/可恢复的后端版本索引（不包含前端草稿）。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "versions": [
      {
        "version_id": "ver_20260428_003",
        "source": "run",
        "source_ref": "run_20260428_001",
        "created_at": "2026-04-28T03:00:00Z"
      },
      {
        "version_id": "ver_20260427_012",
        "source": "save",
        "source_ref": null,
        "created_at": "2026-04-27T10:32:00Z"
      }
    ],
    "retention": {
      "max_count": 100,
      "max_age_days": 30
    },
    "truncated": false
  }
}
```

说明：
- `retention` 告知版本保留策略（数量/时间窗口）。
- `truncated=true` 表示存在历史版本已被淘汰，避免用户误认为“版本丢失是故障”。

---

### SWB-18 — 读取单个配置版本详情

- **Method & path**：`GET /api/v1/strategies/{strategy_name}/versions/{version_id}`
- **语义**：返回指定版本对应的整包 settings（用于对比/恢复预览）。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "version_id": "ver_20260428_003",
    "settings": {}
  }
}
```

---

### SWB-19 — 恢复配置版本

- **Method & path**：`POST /api/v1/strategies/{strategy_name}/versions/{version_id}/restore`
- **语义**：将指定版本覆盖为当前 settings（等价于一次“恢复并保存”）。

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "restored": true,
    "strategy_name": "example",
    "version_id": "ver_20260428_003"
  }
}
```

---

### SWB-20 — 固化当前工作台配置为后端版本

- **Method & path**：`POST /api/v1/strategies/{strategy_name}/versions`
- **语义**：将当前工作台配置（前端传入 settings 快照）固化为后端版本，供“应用到策略”“历史对比”“版本恢复”统一使用。

#### 请求契约

```json
{
  "source": "manual_apply",
  "source_ref": null,
  "settings": {}
}
```

字段说明：
- `source`：建议值 `manual_apply | run | save`
- `source_ref`：可选，`run` 场景可写 `run_id`
- `settings`：完整 settings 快照

#### 响应契约（成功，HTTP 200）

```json
{
  "status": "ok",
  "message": {
    "version_id": "ver_20260428_021",
    "created": true
  }
}
```

---

### Snapshot 存储（专门表，建议）

建议至少两张表：

1. `workbench_snapshot`
   - 主键建议：`(strategy_name, user_key)`
   - 字段：
     - `strategy_name` (varchar)
     - `user_key` (varchar，单机可先固定 `default_user`)
     - `revision` (int)
     - `ui_state_json` (json/text)
     - `working_state_json` (json/text)
     - `updated_at` (datetime)
     - `created_at` (datetime)

2. `workbench_version`
   - 主键：`version_id`
   - 索引建议：`(strategy_name, user_key, created_at desc)`
   - 字段：
     - `version_id` (varchar)
     - `strategy_name` (varchar)
     - `user_key` (varchar)
     - `source` (varchar，建议 `run | save`)
     - `source_ref` (varchar, nullable，run 时可写 `run_id`)
     - `settings_json` (json/text)
     - `created_at` (datetime)

保留策略：
- `version` 仅保留最近 N 条（如 100）；
- 超限按时间淘汰，避免表无限增长。

---

## 修订记录

- **SWB-04 / SWB-05**：单策略整包 settings 读写（实例值契约）。
- **SWB-02 / SWB-03**：左侧下拉与字段联动 profile（候选值契约，必需）。
- **SWB-06 ~ SWB-10**：执行面板（启动 / 状态轮询 / 取消 / 摘要 / 对比版本）。
- **SWB-11 ~ SWB-14**：报告面板（摘要 / 样本表 / 单股K线 / 双栏对比）。
- **SWB-15 ~ SWB-20**：snapshot（专门表）读取/保存 + 配置版本列表/详情/恢复 + 版本固化。

## Roadmap（执行面板）

- **近期（v1）**：执行状态采用 API 轮询（`run_id` + status/progress 持久化），先保证稳定可观测。
- **中期（v1.x）**：在同一状态源上评估新增 SSE 推送，减少前端轮询频率与延迟。
- **后续（worker 改造后）**：当后端引入正式 Queue/Pipeline 系统后，重构执行层事件模型，再决定是否将执行进度通道升级为 SSE/WS 主链路。
- **原则**：无论轮询或推送，先保证统一 run-state 真源，避免 UI 状态与任务真实状态漂移。
