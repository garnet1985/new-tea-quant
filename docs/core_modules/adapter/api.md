# Adapter 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出 Adapter 模块中**用户会直接调用或需要继承的接口**；由框架自动调用的内部函数尽量不列入。架构与设计见 `architecture.md` / `decisions.md`，快速上手见 `overview.md`。

---

## HistoryLoader（历史结果读取）

**模块路径**：`core.modules.adapter.history_loader.HistoryLoader`

### load_stock_history

**描述**：加载指定策略在最新 PriceFactor 模拟版本下，**单只股票**的历史模拟统计信息（胜率、平均收益等）。常用于 Web/API 层按股票展示策略表现。

**函数签名**：`HistoryLoader.load_stock_history(strategy_name: str, stock_id: str) -> Optional[Dict[str, Any]]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名称（对应 `userspace/strategies/{strategy_name}`） |
| `stock_id` | `str` | 股票 ID，如 `"000001.SZ"` |

**输出**：`Optional[Dict[str, Any]]` —— 统计信息字典；若不存在记录则返回 `None`。典型字段包括：

- `win_rate`: 胜率（0~1）  
- `avg_return`: 平均收益率  
- `total_investments`: 总投资次数  
- `win_count` / `loss_count`: 盈利 / 亏损次数  
- `max_return` / `min_return`: 最大 / 最小收益  
- `avg_holding_days`: 平均持有天数  

**Example**：

```python
from core.modules.adapter.history_loader import HistoryLoader

stats = HistoryLoader.load_stock_history(
    strategy_name="my_strategy",
    stock_id="000001.SZ",
)

if stats:
    print("win_rate:", stats["win_rate"])
    print("avg_return:", stats["avg_return"])
```

---

### load_session_summary

**描述**：加载指定策略在最新 PriceFactor 模拟版本下的**会话整体汇总**（session summary），包括全市场的聚合统计。通常用于仪表盘或报告页。

**函数签名**：`HistoryLoader.load_session_summary(strategy_name: str) -> Optional[Dict[str, Any]]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名称 |

**输出**：`Optional[Dict[str, Any]]` —— 会话汇总字典；若不存在则返回 `None`。具体结构由 PriceFactorSimulator 输出定义，一般包含：

- 全局收益分布统计  
- 分股票 / 分区间的聚合指标  
- 元信息（版本号、时间范围等）  

**Example**：

```python
from core.modules.adapter.history_loader import HistoryLoader

summary = HistoryLoader.load_session_summary(strategy_name="my_strategy")
if summary:
    print(summary.get("total_investments"), summary.get("win_rate"))
```

---

## BaseOpportunityAdapter（扩展用）

**模块路径**：`core.modules.adapter.base_adapter.BaseOpportunityAdapter`

### BaseOpportunityAdapter（构造函数）

**描述**：机会适配器基类。用户在 `userspace/adapters/` 下创建自定义 adapter 时，需要继承此类。基类负责按约定路径加载 `settings.py` 配置，并提供基础日志与配置访问工具。

**函数签名**：`BaseOpportunityAdapter(adapter_name: Optional[str] = None)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `adapter_name` | `str \| None` | 适配器名称；为 `None` 时从类名推断（去掉 `Adapter` / `Opportunity` 后缀并转为小写） |

**输出**：无（构造实例）

**Example**（自定义适配器类）：

```python
from typing import List, Dict, Any
from core.modules.adapter.base_adapter import BaseOpportunityAdapter
from core.modules.strategy.models.opportunity import Opportunity


class MyDashboardAdapter(BaseOpportunityAdapter):
    def process(self, opportunities: List[Opportunity], context: Dict[str, Any]) -> None:
        # 使用 self.config 访问 settings.py 中的配置
        top_n = self.get_config("top_n", default=20)
        self.log_info(f"收到 {len(opportunities)} 个机会，将展示前 {top_n} 个")
        # ... 将结果写入缓存 / DB / Web API ...
```

---

### config 属性

**描述**：返回从 `userspace.adapters.{adapter_name}.settings` 加载的配置字典。若找不到配置文件或解析失败，则返回空字典。

**函数签名**：`BaseOpportunityAdapter.config -> Dict[str, Any]`（属性）

**参数**：无

**输出**：`Dict[str, Any]` —— 完整配置字典；未找到配置时为空。

**Example**：

```python
adapter = MyDashboardAdapter()
print(adapter.config.get("output", {}))
```

---

### get_config

**描述**：从适配器配置中按「点号路径」读取配置项（如 `"output.format"`）。不存在时返回默认值。

**函数签名**：`BaseOpportunityAdapter.get_config(key: str, default: Any = None) -> Any`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | `str` | 配置键，支持点号分隔（如 `"output.format"`） |
| `default` | `Any` | 未找到配置时返回的默认值 |

**输出**：`Any` —— 对应配置值或默认值。

**Example**：

```python
fmt = adapter.get_config("output.format", default="json")
```

---

### process（需覆盖）

**描述**：机会适配器的核心方法。框架会在扫描完成后，将机会列表与上下文信息传入此方法，由用户实现具体的落地逻辑（写 DB、推送通知、生成报表等）。

**函数签名**：`BaseOpportunityAdapter.process(opportunities: List["Opportunity"], context: Dict[str, Any]) -> None`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `opportunities` | `List[Opportunity]` | 机会列表（PriceFactor / Scanner 产出的机会，已封装为 dataclass） |
| `context` | `Dict[str, Any]` | 上下文信息，如：`date`（扫描日期）、`strategy_name`、`scan_summary` 等 |

**输出**：`None`（由实现方自行决定如何持久化或输出）

**Example**：见前文 `MyDashboardAdapter` 示例中的 `process` 实现。

---

### 日志辅助方法

**描述**：封装的日志方法，统一加上 adapter_name 前缀，便于排查问题。

**函数签名**：

- `BaseOpportunityAdapter.log_info(message: str) -> None`  
- `BaseOpportunityAdapter.log_warning(message: str) -> None`  
- `BaseOpportunityAdapter.log_error(message: str, exc_info: bool = False) -> None`

**参数（共通）**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `message` | `str` | 日志消息 |
| `exc_info` | `bool` | 仅 `log_error` 使用，是否附带异常堆栈 |

**输出**：`None`

**Example**：

```python
try:
    adapter.process(opportunities, context)
except Exception as e:
    adapter.log_error(f\"处理机会失败: {e}\", exc_info=True)
```

---

## 相关说明

- **读取历史结果**：通过 `HistoryLoader.load_stock_history()` 和 `load_session_summary()` 在上层产品中复用 PriceFactor 模拟结果。  
- **扩展适配器**：在 `userspace/adapters/{adapter_name}/` 创建 `settings.py` 和适配器类，继承 `BaseOpportunityAdapter` 并实现 `process()`。  
- **配置访问**：通过 `config` 属性与 `get_config()` 统一读取适配器配置。  

