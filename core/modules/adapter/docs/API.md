# Adapter 模块 API 文档

本文档采用统一 API 条目格式：函数名、状态、描述、诞生版本、参数（三列表格）、返回值。

---

## BaseOpportunityAdapter

### 函数名
`__init__(self, adapter_name: Optional[str] = None) -> None`

- 状态：`stable`
- 描述：创建 adapter 实例；触发从 `userspace.adapters.<名称>.settings` 加载配置（若模块存在）。名称缺省时由类名推断（去掉 `Adapter` / `Opportunity` 后缀后小写）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `adapter_name` (可选) | `Optional[str]` | 显式适配器名，用于配置路径与日志前缀 |

- 返回值：`None`

---

### 函数名
`config(self) -> Dict[str, Any]`

- 状态：`stable`
- 描述：实例属性（`@property`），返回已加载的 settings/config 字典，可能为空 `{}`。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`Dict[str, Any]`

---

### 函数名
`get_config(self, key: str, default: Any = None) -> Any`

- 状态：`stable`
- 描述：按点号路径读取嵌套配置（如 `"output.format"`）；路径不存在返回 `default`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `key` | `str` | 点号分隔键路径 |
| `default` (可选) | `Any` | 默认值 |

- 返回值：`Any`

---

### 函数名
`process(self, opportunities: List[Opportunity], context: Dict[str, Any]) -> None`

- 状态：`stable`
- 描述：抽象方法，子类必须实现：处理一次扫描得到的 `Opportunity` 列表与上下文。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `opportunities` | `List[Opportunity]` | 机会列表 |
| `context` | `Dict[str, Any]` | 如 `date`、`strategy_name`、`scan_summary` 等 |

- 返回值：`None`

---

### 函数名
`log_info(self, message: str) -> None`

- 状态：`stable`
- 描述：以 `[adapter_name]` 前缀写 `INFO` 日志。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `message` | `str` | 文本 |

- 返回值：`None`

---

### 函数名
`log_warning(self, message: str) -> None`

- 状态：`stable`
- 描述：以 `[adapter_name]` 前缀写 `WARNING` 日志。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `message` | `str` | 文本 |

- 返回值：`None`

---

### 函数名
`log_error(self, message: str, exc_info: bool = False) -> None`

- 状态：`stable`
- 描述：以 `[adapter_name]` 前缀写 `ERROR` 日志；`exc_info` 为真时附带异常栈。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `message` | `str` | 文本 |
| `exc_info` (可选) | `bool` | 是否记录异常信息，默认 `False` |

- 返回值：`None`

---

### 函数名
`default_output(opportunities: List[Opportunity], context: Dict[str, Any]) -> None`

- 状态：`stable`
- 描述：静态方法；在控制台打印简要扫描结果（无机会时亦有提示）。由 **`AdapterDispatcher`** 在「未配置 adapter」或「全部 adapter 失败」时调用。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `opportunities` | `List[Opportunity]` | 机会列表 |
| `context` | `Dict[str, Any]` | 上下文 |

- 返回值：`None`

---

## validate_adapter

### 函数名
`validate_adapter(adapter_name: str) -> Tuple[bool, str]`

- 状态：`stable`
- 描述：校验给定名称是否对应可加载的 userspace 模块，且存在可实例化的 `BaseOpportunityAdapter` 子类。用于策略设置校验，不执行 `process` 业务逻辑。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `adapter_name` | `str` | 与 `userspace/adapters/<名称>/` 目录名一致 |

- 返回值：`(is_valid, error_message)`；合法时 `error_message` 为空字符串。

---

## HistoryLoader

### 函数名
`load_stock_history(strategy_name: str, stock_id: str) -> Optional[Dict[str, Any]]`

- 状态：`stable`
- 描述：在最新价格模拟版本目录下读取单股结果 JSON，聚合投资记录并返回胜率、收益等统计；无法解析时返回 `None`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名 |
| `stock_id` | `str` | 股票代码 |

- 返回值：统计字典，字段见源码文档字符串（如 `win_rate`、`avg_return`、`completed_investments` 等）；无数据时为 `None`。

---

### 函数名
`load_session_summary(strategy_name: str) -> Optional[Dict[str, Any]]`

- 状态：`stable`
- 描述：读取当前解析到的模拟版本下的会话汇总 JSON；文件不存在或失败时返回 `None`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名 |

- 返回值：`Dict[str, Any]` 或 `None`

---

## 示例

```python
from typing import Any, Dict, List

from core.modules.adapter import BaseOpportunityAdapter
from core.modules.strategy.models.opportunity import Opportunity


class EchoAdapter(BaseOpportunityAdapter):
    def process(
        self,
        opportunities: List[Opportunity],
        context: Dict[str, Any],
    ) -> None:
        self.log_info(f"{context.get('date')}: {len(opportunities)} opportunities")
```

策略 `scanner.adapters` 中包含目录名 `echo`（且 `userspace/adapters/echo/adapter.py` 中类继承 `BaseOpportunityAdapter`）后，由 **`AdapterDispatcher`** 在扫描结束时调用。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
