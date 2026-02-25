# Data Source 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出各 API。仅包含用户需要主动调用或需覆盖的接口；由框架自动调用的构造函数、内部方法等不列入。架构说明见 [architecture.md](./architecture.md)。

---

## DataSourceManager

### DataSourceManager（构造函数）

**描述**：创建数据源管理器，用于后续执行所有启用的数据源。约定：执行前需保证 `userspace/data_source/mapping.py`（或 mapping.json）及各 Handler 的 config 已配置。

**函数签名**：`DataSourceManager(is_verbose: bool = False)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `is_verbose` | `bool` | 是否输出更详细日志，默认 `False` |

**输出**：无（构造实例）

**用例**：

```python
from core.modules.data_source.data_source_manager import DataSourceManager

manager = DataSourceManager(is_verbose=False)
```

---

### execute

**描述**：执行所有启用的数据源。流程：发现 mapping → 发现 Provider/Config/Handler → 按依赖顺序执行各 Handler。是否写库由各 config 的 `is_dry_run` 控制（True 则不写库）。

**函数签名**：`DataSourceManager.execute() -> None`

**参数**：无

**输出**：`None`

**用例**：

```python
manager = DataSourceManager()
manager.execute()
```

---

## BaseProvider（扩展用）

第三方 API 封装基类。子类必须定义类属性：`provider_name`、`requires_auth`、`auth_type`、`api_limits`（及可选 `default_rate_limit`），并实现 `_initialize()`。Provider 由框架实例化，用户仅需在子类中**覆盖**下列方法（如需要）。

### handle_error

**描述**：将第三方 API 抛出的异常转换为框架统一的 `ProviderError`。约定：子类可覆盖以处理特定错误类型或补充信息。

**函数签名**：`BaseProvider.handle_error(error: Exception, api_name: str) -> ProviderError`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `error` | `Exception` | 原始异常 |
| `api_name` | `str` | 发生错误的 API 方法名 |

**输出**：`ProviderError` — 含 provider 名、api 名、原始异常等信息

**Example**：

```python
try:
    return self.some_api_call()
except Exception as e:
    raise self.handle_error(e, "some_api_call")
```

---

## DataSourceConfig

数据源配置由框架从 config 加载并注入到 Handler 的 `self.context["config"]`。用户仅通过以下 getter 读取，不直接构造 Config。

### DataSourceConfig 常用 getter

**描述**：通过 getter 读取配置，避免直接访问内部属性。约定：写 Handler 时优先用这些方法。

**函数签名**（部分）：`get_table_name()`, `get_save_mode()`, `get_is_dry_run()`, `get_apis()`, `get_renew_mode()`, `get_default_date_range_years()`, `get_merge_by_key()`, `get_group_by_entity_list_name()` 等（完整列表见 `config.py`）。

**参数**：无（各 getter 无参）

**输出**：依方法不同（str / bool / Dict / List 等）

**用例**：

```python
config = self.context["config"]
table = config.get_table_name()
is_dry = config.get_is_dry_run()
apis = config.get_apis()
```

---

## ApiJob

表示单次 API 调用任务，由 Handler 在预处理阶段构建，由框架执行器执行。用户（在 Handler 内）通过构造函数创建 ApiJob，不要直接调用 `ApiJob.execute()`。

### ApiJob（构造函数）

**描述**：构造一个 API 任务。约定：`api_name` 或 `method` 至少有一个；`depends_on` 为依赖的 job_id 列表，用于拓扑排序；`rate_limit` 为每分钟请求数（0 表示使用 Provider 声明）。

**函数签名**：`ApiJob(api_name: Optional[str] = None, provider_name: Optional[str] = None, method: Optional[str] = None, params: Optional[Dict[str, Any]] = None, api_params: Optional[Dict[str, Any]] = None, depends_on: Optional[List[str]] = None, rate_limit: int = 0, job_id: Optional[str] = None)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `api_name` | `Optional[str]` | API 名称，默认可用 method 代替 |
| `provider_name` | `Optional[str]` | Provider 名，如 `"tushare"` |
| `method` | `Optional[str]` | Provider 内方法名 |
| `params` | `Optional[Dict[str, Any]]` | 调用参数（会注入日期等后传给 provider.method(**params)） |
| `api_params` | `Optional[Dict[str, Any]]` | 原始 API 配置（如 config 中的 apis[*]） |
| `depends_on` | `Optional[List[str]]` | 依赖的 job_id 列表 |
| `rate_limit` | `int` | 每分钟请求数，0 表示用 Provider 声明 |
| `job_id` | `Optional[str]` | 任务 ID，默认用 api_name |

**输出**：无（构造实例）

**用例**：

```python
from core.modules.data_source.data_class.api_job import ApiJob

job = ApiJob(
    api_name="get_daily_kline",
    provider_name="tushare",
    method="get_daily_kline",
    params={"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250130"},
    depends_on=[],
)
```

---

## 保留依赖

保留依赖在注入时由框架直接解析，mapping 中的 data source key 不能使用这些关键字。若自定义逻辑需要解析保留依赖（如 `latest_trading_date`），可调用下列函数。

### resolve_reserved_dependency

**描述**：根据保留依赖 key 解析出依赖值。当前仅支持 `latest_trading_date`，返回形状为 `[{"date": "YYYYMMDD"}]`，与下游期望一致。约定：`dep_key` 必须在 `RESERVED_DEPENDENCY_KEYS` 中。

**函数签名**：`resolve_reserved_dependency(dep_key: str) -> Any`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `dep_key` | `str` | 保留依赖关键字，如 `"latest_trading_date"` |

**输出**：`Any` — 如 `latest_trading_date` 返回 `[{"date": "20250130"}]`

**异常**：`ValueError` — `dep_key` 不在保留字中或未实现时

**用例**：

```python
from core.modules.data_source.reserved_dependencies import resolve_reserved_dependency, RESERVED_DEPENDENCY_KEYS

# RESERVED_DEPENDENCY_KEYS = frozenset({"latest_trading_date"})
result = resolve_reserved_dependency("latest_trading_date")
# result == [{"date": "20250130"}]
```

---

## 相关文档

- [Data Source 架构](./architecture.md)
- [Data Manager](../data_manager/architecture.md)
