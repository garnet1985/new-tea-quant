# Strategy 模块 API 文档

**版本：** `0.2.0`

本文档覆盖 **`core.modules.strategy`** 包导出与主要组件入口；Worker 与模型字段以源码为准。

---

## 枚举类型（包导出）

自 **`core.modules.strategy`** 导入：

### ExecutionMode

| 成员 | 值 |
|------|-----|
| `SCAN` | `scan` |
| `SIMULATE` | `simulate` |

### OpportunityStatus / SellReason

见 **`enums.py`**（扫描、回测与枚举共用状态机语义）。

---

## StrategyManager

### 函数名
`__init__(self, is_verbose: bool = False)`

- 状态：`stable`
- 描述：构造 **`DataManager`**、契约缓存与 **`DataContractManager`**，并 **`StrategyDiscoveryHelper.discover_strategies()`** 填充 **`validated_strategies`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `is_verbose` (可选) | `bool` | 是否详细日志 |

- 返回值：无

---

### 函数名
`lookup_strategy_info(self, strategy_name: str) -> Optional[StrategyInfo]`

- 状态：`stable`
- 描述：先查缓存，再尝试从 **`userspace/strategies/<name>`** 加载。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略目录名 |

- 返回值：**`StrategyInfo`** 或 **`None`**

---

### 函数名
`scan(self, strategy_name: Optional[str] = None, date: Optional[str] = None) -> None`

- 状态：`stable`
- 描述：对启用策略在指定日（默认今日 `YYYYMMDD`）构建 scan jobs，**`ProcessWorker`** 执行 **`BaseStrategyWorker`**，结果写入 **`OpportunityService`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` (可选) | `Optional[str]` | `None` 表示所有 **`is_enabled`** 策略 |
| `date` (可选) | `Optional[str]` | 扫描日 |

- 返回值：`None`

---

### 函数名
`simulate(self, strategy_name: Optional[str] = None, session_id: Optional[str] = None, date: Optional[str] = None) -> None`

- 状态：`stable`
- 描述：逐日 simulate（价格层主线回测）；`session_id` 缺省时 **`SessionManager.create_session()`**；股票列表受 **`price_simulator.use_sampling`** 与 **`sampling`** 块影响。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` (可选) | `Optional[str]` | `None` 表示所有启用策略 |
| `session_id` (可选) | `Optional[str]` | 会话 id |
| `date` (可选) | `Optional[str]` | 解析逻辑见实现（如 latest） |

- 返回值：`None`

---

### 函数名
`list_strategies(self) -> List[str]` / `get_strategy_info(self, strategy_name: str) -> Optional[StrategyInfo]`

- 状态：`stable`
- 描述：列出已发现且校验通过的策略名；**`get_strategy_info`** 同 **`lookup_strategy_info`**。
- 诞生版本：`0.2.0`

---

### 函数名
`clear_contract_cache(self) -> None` / `contract_cache`（property）

- 状态：`stable`
- 描述：主进程 **`ContractCacheManager`** 访问与清空。
- 诞生版本：`0.2.0`

---

## BaseStrategyWorker

子类位于 **`userspace.strategies.<name>.strategy_worker`**。

### 函数名
`run(self) -> Dict[str, Any]`

- 状态：`stable`
- 描述：子进程入口；按 **`execution_mode`** 分 **`_execute_scan`** / **`_execute_simulate`**。
- 诞生版本：`0.2.0`
- 返回值：scan 为 **`{success, stock_id, opportunity}`**；simulate 为 **`{success, stock_id, settled}`**（**`settled`** 为 dict 列表）。

---

### 函数名
`scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Opportunity]`

- 状态：`stable`（抽象）
- 描述：用户实现；**`data`** 为截至当前业务日的切片（含 klines 及指标列等）。
- 诞生版本：`0.2.0`

---

## OpportunityEnumerator

### 函数名
`OpportunityEnumerator.enumerate(strategy_name, start_date, end_date, stock_list, max_workers='auto', base_settings=None) -> List[Dict[str, Any]]`

- 状态：`stable`
- 描述：全量枚举并落盘版本目录；返回机会字典列表（摘要用途，以磁盘为准）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名 |
| `start_date` / `end_date` | `str` | `YYYYMMDD` |
| `stock_list` | `List[str]` | 股票代码 |
| `max_workers` (可选) | `Union[str, int]` | `'auto'` 或正整数 |
| `base_settings` (可选) | `Optional[StrategySettings]` | 避免重复 import |

- 返回值：`List[Dict[str, Any]]`

---

## PriceFactorSimulator

### 函数名
`run(self, strategy_name: str) -> Dict[str, Any]`

- 状态：`stable`
- 描述：见 **[simulator_price_factor.md](components/simulator_price_factor.md)**。
- 诞生版本：`0.2.0`

---

## CapitalAllocationSimulator

### 函数名
`run(self, strategy_name: str) -> Dict[str, Any]`

- 状态：`stable`
- 描述：见 **[simulator_capital_allocation.md](components/simulator_capital_allocation.md)**。
- 诞生版本：`0.2.0`

---

## StrategySettings / Opportunity

- **`StrategySettings`**：**`models.strategy_settings`**与 **`data_classes.strategy_settings`** 并存；Manager 与 Worker 常用 **`from_dict` / `to_dict`**。
- **`Opportunity`**：**`models.opportunity`**，序列化与 **`from_dict`** 用于 JSON 与 Worker 返回。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
- [组件索引](components/README.md)
