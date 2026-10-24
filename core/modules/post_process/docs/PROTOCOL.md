# Adapter 出口协议

**状态：** 已落地（`modules.post_process` 0.3.0 / `contracts`）  
**版本：** `0.3.0`

Adapter 的核心出口是三层标准协议（建议用三个 dataclass 表达）。  
协议是后续处理里每个 component 的**标准协议 input**（可另有依赖产出，见 [POST_PROCESS.md](./POST_PROCESS.md)）；如何删减、重组、副作用由 component 自行决定。

**不在本协议内：** 可交易演示对象（如仓位金额/股数/仓位比）、具体通知/下单实现、回测产物读取细节、PostProcess 编排。

---

## 三层一览

```text
ScanSessionReport                 # 一次扫描会话（可含多策略）
  └── strategies: List[StrategyScanReport]
        └── opportunities: List[Opportunity]
```

| 层 | 类名（建议） | 职责 |
|----|--------------|------|
| 会话 | `ScanSessionReport` | 一次扫描跑批的顶层出口；单策略时 `strategies` 长度为 1 |
| 单策略 | `StrategyScanReport` | 一个策略一次扫描：报告者、目标、时间、该策略下的机会集 |
| 机会 | `Opportunity` | 单条机会主体：哪个标的、在什么价位被点出 |

命名说明：顶层不用裸名 `ScanReport`，以免与「单策略报告」混淆；会话语义用 `ScanSessionReport`。

---

## 1. `Opportunity`（标准机会）

**一句话：** 哪个标的、在什么触发价/日被识别为机会。

### 字段

| 字段 | 类型 | 必选 | 说明 |
|------|------|------|------|
| `id` | `str` | ✓ | 稳定标识（策略内唯一即可；建议含策略/标的/日/序号信息） |
| `entity_id` | `str` | ✓ | 标的代码，如 `000001.SZ` |
| `entity_name` | `str` | | 名称 |
| `entity_exchange` | `str` | | 交易所等 |
| `entity_type` | `str` | | 如 `stock` |
| `trigger_date` | `str` | ✓ | 触发日 |
| `trigger_price` | `float` | ✓ | 信号价（策略所用口径） |
| `trigger_price_raw` | `float` | | 可选裸价 |
| `trigger_price_hfq` | `float` | | 可选后复权价 |
| `snapshot` | `dict` | | 决策归因袋（对应内部 `signal_snapshot`）；可空 |

### 不放进本层

- 仓位、账户、下单方式  
- 止盈 / 止损 / 持有规则（属 `StrategyScanReport.goal`）  
- 回测成绩、app 内二次查询结果（由 component 自取）

### 最小校验

`id`、`entity_id`、`trigger_date`、`trigger_price` 存在且类型正确。

### 与 strategy 内部对象

策略引擎内部已有 `Opportunity` dataclass（含 `stock`、`record_of_today`、`meta` 等）。  
**本协议是 adapter 出口视图**：由内部对象映射而来；不必也不应把内部实现细节（如整根当日 bar）默认塞进协议。映射关系见文末。

---

## 2. `StrategyScanReport`（标准单策略扫描报告）

**一句话：** 哪个策略、在什么扫描日、带着什么目标，报出了一批机会。

### 字段

| 字段 | 类型 | 必选 | 说明 |
|------|------|------|------|
| `strategy_name` | `str` | ✓ | 报告者：策略标识 |
| `strategy_version` | `str` | | 可空 |
| `scan_date` | `str` | ✓ | 该策略本次扫描锚定日 |
| `emitted_at` | `str` | | 本报告生成时刻（ISO 推荐） |
| `goal` | `dict` | ✓* | 策略目标摘要；见下。实现初期可允许空 dict，但语义上「应有目标可遵守」 |
| `opportunities` | `list[Opportunity]` | ✓ | 可为 `[]` |

\* `goal` 建议始终提供键；无配置时用 `{}`，由校验策略决定是否 warn。

### `goal` 语义

对应策略 `settings.goal` 的**摘要**（止损 / 止盈 / 持有到期等），不是整份 settings 倾销。

形态示例（与引擎 goal 块对齐即可，不在此锁死 schema）：

```text
goal:
  stop_loss: ...
  take_profit: ...
  expiration: ...
```

**给 component 的准则（非字段）：**

- 基于本报告做后续动作时，**默认遵守 `goal`**  
- 若要改止损 / 止盈 / 持有等，必须在用户自己的 component 里**显式**修改，不得静默覆盖

### 最小校验

`strategy_name`、`scan_date` 非空；每个 `opportunities[i]` 通过 `Opportunity` 校验。

### 为何单独一层

多策略联合扫描时，每个策略的 `goal` 不同。  
若把多策略机会扁平成一份「大报告」却只挂一个 goal，「默认遵守目标」无法成立。  
因此：**一策略 → 一份 `StrategyScanReport`** 是原子单位。

---

## 3. `ScanSessionReport`（标准扫描会话报告）

**一句话：** 一次扫描会话的顶层出口；可包含一份或多份单策略报告。

### 字段

| 字段 | 类型 | 必选 | 说明 |
|------|------|------|------|
| `scan_date` | `str` | ✓ | 本次会话锚定日（通常与各策略 `scan_date` 一致） |
| `emitted_at` | `str` | | 会话出口生成时刻 |
| `strategies` | `list[StrategyScanReport]` | ✓ | 长度 ≥ 0；单策略场景长度为 1 |

字段名用 `strategies` 而非 `reports`，避免「报告里还有报告」的口头歧义。

### 场景

| 场景 | 形态 |
|------|------|
| 单策略 scan（现状主路径） | `strategies` 含 1 个 `StrategyScanReport` |
| 多策略联合扫描 | `strategies` 含 N 个，各带自己的 `goal` 与机会集 |

同一标的被多策略同时命中 → **多条 `Opportunity`，分属不同 `StrategyScanReport`**。  
去重或合并仓位是下游 component 的事，不在协议层合并。

### 最小校验

`scan_date` 非空；每个 `strategies[i]` 通过 `StrategyScanReport` 校验。

---

## Adapter 职责（相对本协议）

**In scope（协议相关）：**

- 将扫描结果校验并规范化为 `ScanSessionReport`（内含 `StrategyScanReport` / `Opportunity`）  
- 把该对象交给 **PostProcess** 作为各 component 的标准协议 input  

**Out of scope：**

- 扫描调度、多策略编排细节（由 strategy / runner 决定何时组装会话）  
- PostProcess / component 实现细节（见 [POST_PROCESS.md](./POST_PROCESS.md)）  
- 可交易演示协议、通知/券商实现  
- 强迫 component 写回本协议  

运行时：`PostProcessDispatcher` → `PostProcess.build_session_report` → `PostProcess.run_post_processor`。

---

## Component 与本协议

- 标准协议 input：始终是同一份 `ScanSessionReport`  
- 若 component 声明了 `depends_on`，另有一路 **依赖产出**（`deps` map）；详见 [POST_PROCESS.md](./POST_PROCESS.md)  
- 只需单策略 / 单机会时：自行从 `strategies` / `opportunities` 向下取  
- 「建议买多少 / 演示下单」等局部类型：**不属于**本三层协议  

---

## 与内部 `Opportunity` 的映射（实现对照）

| 协议 `Opportunity` | 策略内部（示意） |
|--------------------|------------------|
| `entity_id` / `entity_name` / … | `stock.id` / `stock.name` / … |
| `trigger_date` / `trigger_price*` | `trigger_date` / `trigger_price*` |
| `snapshot` | `signal_snapshot` |
| `id` | 由策略名 + 标的 + 日 + `meta.opportunity_id` 等规范生成 |
| （默认不进协议） | `record_of_today`、完整 `metadata` 等 — component 若需要再向 app 查询 |

| 协议 `StrategyScanReport` | 来源（示意） |
|---------------------------|--------------|
| `strategy_name` / `strategy_version` | `contributor`、策略 meta |
| `scan_date` | scanner context `date` |
| `goal` | `settings.goal` 摘要 |
| `opportunities` | 映射后的协议机会列表 |

| 协议 `ScanSessionReport` | 来源（示意） |
|--------------------------|--------------|
| `scan_date` / `emitted_at` | 会话层时间 |
| `strategies` | 一次或多次单策略扫描结果的聚合 |

---

## 建议 dataclass 落点（实现时）

已放在 `core.modules.post_process.contracts`（与 `BaseAdapter` 一并导出）。  
避免与 `strategy` 内部 `Opportunity` 在文档与 import 路径上混淆。

---

## 相关文档

- [后续处理 PostProcess](./POST_PROCESS.md)  
- [架构](./ARCHITECTURE.md)  
- [设计](./DESIGN.md)  
- [API](../API.md)  
