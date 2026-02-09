# Data Source 模块 API 文档

> 本文档描述 Data Source 模块的公共 API（类、方法、参数与返回值）。架构与设计决策见 [architecture.md](./architecture.md) 与 [decisions.md](./decisions.md)。

---

## 1. 入口与协调层

### 1.1 DataSourceManager

**模块路径**：`core.modules.data_source.data_source_manager.DataSourceManager`

数据源管理器：负责发现 mapping、config、绑定表 schema，创建 Handler 与 Provider 实例，并委托执行调度器运行。

#### 构造函数

```python
DataSourceManager(is_verbose: bool = False)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `is_verbose` | bool | 是否输出详细日志（保留以兼容现有代码） |

#### 方法

| 方法 | 说明 |
|------|------|
| `execute()` | 清空缓存 → 发现 mapping → 发现 providers → 发现并创建所有启用的 Handler 实例 → 调用 `DataSourceExecutionScheduler.run(handler_instances, mappings)` 执行。是否写库由各 handler 的 config 顶层 `is_dry_run`（bool）控制。 |

#### 内部流程（供理解）

- `_discover_mappings()`：从 `userspace/data_source/mapping.py`（或兼容 `mapping.json`）加载 `DATA_SOURCES`，返回 `HandlerMapping`。
- `_discover_config(data_source_key)`：从 `userspace/data_source/handlers/{data_source_key}/config.py` 加载 `CONFIG`，构造 `DataSourceConfig`。
- `_get_schema_for_handler(config)`：根据 `config.get_table_name()` 从 `DataManager.get_table(table).load_schema()` 获取表 schema（dict）。
- `_discover_handler(data_source_key, mappings)`：根据 mapping 中的 handler 路径动态导入 Handler 类。
- `_discover_providers()`：发现并实例化所有 Provider。

---

### 1.2 DataSourceExecutionScheduler

**模块路径**：`core.modules.data_source.execution_scheduler.DataSourceExecutionScheduler`

执行调度器：按依赖顺序串行执行各数据源 Handler，并在执行时注入依赖数据源的结果到 context。

#### 构造函数

```python
DataSourceExecutionScheduler(is_verbose: bool = False)
```

#### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `run` | `run(handler_instances, mappings)` | 对 handlers 做拓扑排序 → 按序执行每个 handler.execute(dependencies_data) → 可选重试失败的数据源 |

---

## 2. Handler 层

### 2.1 BaseHandler

**模块路径**：`core.modules.data_source.base_class.base_handler.BaseHandler`

Handler 基类：定义执行管线（预处理 → 执行 API → 后处理）与可覆盖的生命周期钩子。

#### 构造函数

```python
BaseHandler(
    data_source_key: str,
    schema: Any,                    # 表 schema dict（来自 DataManager.get_table(...).load_schema()）
    config: DataSourceConfig,
    providers: Dict[str, BaseProvider],
    depend_on_data_source_names: List[str] = None,
)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `data_source_key` | str | 数据源配置键（mapping 中的 key） |
| `schema` | dict | 绑定表的 schema（`name`, `primaryKey`, `fields` 等） |
| `config` | DataSourceConfig | 该数据源的配置 |
| `providers` | Dict[str, BaseProvider] | Provider 名称 → 实例 |
| `depend_on_data_source_names` | List[str] | 依赖的数据源 key 列表 |

构造后可通过 `self.context` 访问上述内容及 `data_manager`、`depend_on_data_source_names`。

#### 公开方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `get_key` | `get_key() -> Optional[str]` | 返回 `data_source_key` |
| `get_dependency_data_source_names` | `get_dependency_data_source_names() -> List[str]` | 返回依赖的数据源 key 列表 |
| `execute` | `execute(dependencies_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]` | 同步执行入口：预处理 → 执行 API → 后处理 → 当 `context["is_dry_run"]` 为 False 时先调用 `on_before_save`（用户 save）再系统写入绑定表，返回标准化后的数据（如 `{"data": [...]}`） |

#### 生命周期钩子（子类可覆盖）

| 钩子 | 签名 | 调用时机 |
|------|------|----------|
| `on_prepare_context` | `on_prepare_context(context: Dict) -> Dict` | 注入全局依赖之后、构建 ApiJobs 之前；用于派生/注入上下文 |
| `on_calculate_date_range` | `on_calculate_date_range(context, apis) -> None \| Tuple[str,str] \| Dict[str,Tuple[str,str]]` | 日期范围计算；返回 `None` 则使用默认 RenewManager 逻辑 |
| `on_before_fetch` | `on_before_fetch(context, apis: List[ApiJob]) -> List[ApiJob]` | 日期已注入 ApiJobs 之后；可增删改 ApiJobs |
| `on_after_fetch` | `on_after_fetch(context, fetched_data, apis)` | 抓取完成后、标准化之前；默认按 `group_by` 做分组或统一聚合 |
| `on_after_mapping` | `on_after_mapping(context, mapped_records: List[Dict]) -> List[Dict]` | 字段映射之后、schema 应用之前；可补字段、过滤、转换 |
| `on_after_normalize` | `on_after_normalize(context, normalized_data: Dict)` | 标准化之后；默认清洗 NaN，可自定义 |
| `on_before_save` | `on_before_save(context, normalized_data: Dict) -> None` | 用户 save 钩子：在系统写入绑定表之前调用；`context["is_dry_run"]` 为 True 时不调用 |
| `on_thread_execution_error` | `on_thread_execution_error(error, context, apis)` | 执行阶段异常时（不阻止异常传播） |
| `on_bundle_execution_error` | `on_bundle_execution_error(error, context, apis)` | 单 bundle 执行异常时 |

其他钩子（如 `on_after_single_api_job_complete`、`on_after_single_api_job_bundle_complete` 等）见源码，多为扩展点。

---

## 3. Provider 层

### 3.1 BaseProvider

**模块路径**：`core.modules.data_source.base_class.base_provider.BaseProvider`

第三方数据源提供者基类（抽象类）：纯 API 封装，声明认证与限流。

#### 类属性（子类必须定义）

| 属性 | 类型 | 说明 |
|------|------|------|
| `provider_name` | str | 如 `"tushare"` |
| `requires_auth` | bool | 是否需要认证 |
| `auth_type` | Optional[str] | `"token"` \| `"api_key"` \| None |
| `api_limits` | Dict[str, int] | API 方法名 → 每分钟请求数 |
| `default_rate_limit` | Optional[int] | 未在 `api_limits` 中声明的 API 的默认限流 |

#### 构造函数

```python
BaseProvider(config: Dict[str, Any] = None)
```

`config` 为 `None` 时，按约定从文件或环境变量加载（如 tushare 的 `auth_token.txt` 或 `TUSHARE_TOKEN`）。

#### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `get_api_limit` | `get_api_limit(api_name: str) -> Optional[int]` | 返回该 API 的每分钟限流数 |
| `get_metadata` | `get_metadata() -> Dict` | 返回 provider 元信息（name、auth、limits） |
| `handle_error` | `handle_error(error, api_name: str) -> ProviderError` | 将第三方异常封装为 `ProviderError` |

子类必须实现：`_initialize()`（如初始化 API 客户端）。

---

## 4. 配置与映射

### 4.1 DataSourceConfig

**模块路径**：`core.modules.data_source.data_class.config.DataSourceConfig`

数据源配置：由 config.py 的 `CONFIG` 字典构造，提供类型化访问与校验。

#### 构造函数

```python
DataSourceConfig(config_dict: Dict[str, Any], data_source_key: str = None)
```

#### 常用方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `get(key, default=None)` | Any | 兼容 dict 的取值 |
| `is_valid()` | bool | 校验基本信息、renew、result_group_by、apis 等 |
| `get_table_name()` | str | 绑定表名（仅顶层 `table`） |
| `get_renew_mode()` | Optional[UpdateMode] | incremental / rolling / refresh 等 |
| `get_date_field()` | str | 日期字段名 |
| `get_date_format()` | str | 日期粒度（如 daily/monthly/quarterly） |
| `get_apis()` | Dict[str, Any] | apis 配置字典 |
| `is_per_entity()` | bool | 是否按实体分组（是否配置 result_group_by） |
| `get_group_by()` | Dict \| None | result_group_by 配置 |
| `get_group_by_key()` | Optional[str] | 实体标识字段（by_key） |
| `get_group_by_entity_list_name()` | Optional[str] | 实体列表名（list） |
| `get_rolling_unit()` | Optional[str] | 滚动单位（如 daily/monthly） |
| `get_rolling_length()` | int | 滚动窗口长度 |
| `get_renew_if_over_days()` | Optional[Dict] | 「超过 N 天再续跑」配置 |
| `get_renew_extra()` | Dict | renew.extra 扩展配置 |
| `get_merge_by_key()` | Optional[str] | 多 API 合并时的 key |
| `to_dict()` | Dict | 原始配置字典副本 |

---

### 4.2 HandlerMapping

**模块路径**：`core.modules.data_source.data_class.handler_mapping.HandlerMapping`

mapping 的封装：仅包含 `is_enabled=True` 的 data source，并提供查询接口。

#### 构造函数

```python
HandlerMapping(data_sources: Dict[str, Dict[str, Any]])
```

`data_sources` 即 mapping.py 中的 `DATA_SOURCES`（或 mapping.json 的 `data_sources`）。

#### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `get_enabled` | `get_enabled() -> Dict[str, Dict]` | 返回所有启用的 data source 配置 |
| `get_handler_info` | `get_handler_info(data_source_key: str) -> Dict` | 返回该 key 的配置（含 handler 路径、depends_on 等） |
| `get_depend_on_data_source_names` | `get_depend_on_data_source_names(data_source_key: str) -> List[str]` | 返回该数据源声明的依赖 key 列表 |
| `is_dependency_for_downstream` | `is_dependency_for_downstream(data_source_key: str) -> bool` | 是否有其他数据源依赖该 key（用于决定是否缓存结果） |

---

## 5. 任务与执行

### 5.1 ApiJob

**模块路径**：`core.modules.data_source.data_class.api_job.ApiJob`

单次 API 调用的描述：Provider、方法、参数、依赖、限流。

#### 构造函数

```python
ApiJob(
    api_name: Optional[str] = None,
    provider_name: Optional[str] = None,
    method: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    api_params: Optional[Dict[str, Any]] = None,
    depends_on: Optional[List[str]] = None,
    rate_limit: int = 0,
    job_id: Optional[str] = None,
)
```

| 参数 | 说明 |
|------|------|
| `api_name` | 配置中的 API 名；未传时用 `method` |
| `provider_name` | Provider 名称 |
| `method` | 方法名 |
| `params` | 调用参数（会注入 start_date/end_date 等） |
| `api_params` | 原始 API 配置引用 |
| `depends_on` | 依赖的 job_id 列表 |
| `rate_limit` | 每分钟请求数 |
| `job_id` | 未传时用 `api_name` |

属性：`api_name`, `job_id`, `provider_name`, `method`, `params`, `api_params`, `depends_on`, `rate_limit`。  
`execute()` 为占位，实际执行由上层执行器负责。

---

### 5.2 ApiJobBundle

**模块路径**：`core.modules.data_source.data_class.api_job_bundle.ApiJobBundle`

一批需一起执行的 ApiJob（如某一实体的多 API 调用）。

#### 属性（dataclass）

| 属性 | 类型 | 说明 |
|------|------|------|
| `bundle_id` | str | 批次 ID |
| `apis` | List[ApiJob] | 本批次 ApiJob 列表 |
| `tuple_order_map` | Optional[str] | 可选描述 |
| `start_date` | Optional[str] | 本批次统一开始日期 |
| `end_date` | Optional[str] | 本批次统一结束日期 |

#### 静态方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `to_id` | `to_id(data_source_key: str) -> str` | 生成标准化 bundle_id，如 `"{data_source_key}_batch"` |

---

## 6. Renew 编排

### 6.1 RenewManager

**模块路径**：`core.modules.data_source.renew_manager.RenewManager`

根据 renew 模式与表状态决定日期范围，并将日期注入到 ApiJob 的 params 中（由 BaseHandler 内部使用）。

#### 构造函数

```python
RenewManager(data_manager=None)
```

#### 常用方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `is_date_range_specified` | `is_date_range_specified(context) -> bool` | context 是否已包含 start_date/end_date |
| `get_renew_mode` | `get_renew_mode(context) -> UpdateMode` | 从 context.config 取续跑模式 |
| `has_rolling_time_range` | `has_rolling_time_range(context) -> bool` | 是否配置了 rolling_unit + rolling_length |
| `is_table_empty` | `is_table_empty(context) -> bool` | 目标表是否为空（先看 context，再查 DB） |

日期范围计算由内部调用 IncrementalRenewService / RollingRenewService / RefreshRenewService 完成。

---

## 7. 异常类

### 7.1 DataSourceError

**模块路径**：`core.modules.data_source.data_class.error.DataSourceError`

```python
DataSourceError(message: str)
```

通用数据源异常，属性：`message`。

---

### 7.2 ProviderError

**模块路径**：`core.modules.data_source.data_class.error.ProviderError`

```python
ProviderError(provider: str, api: str, original_error: Exception)
```

Provider 调用异常，属性：`provider`、`api`、`original_error`；`str(e)` 为 `[{provider}.{api}] {original_error}`。

---

## 8. 用户侧约定（与 API 配合）

| 约定 | 说明 |
|------|------|
| **mapping.py** | `userspace/data_source/mapping.py` 中定义 `DATA_SOURCES`（dict），每项含 `handler`、`is_enabled`、`depends_on` 等。 |
| **config.py** | `userspace/data_source/handlers/{data_source_key}/config.py` 中定义 `CONFIG`（dict），含顶层 `table`、`renew`、`apis`、`result_group_by` 等；可选 **`is_dry_run`: bool**（该数据源是否仅试跑不写入，便于调试）。 |
| **Schema** | 与 DB 公用：由 `config.get_table_name()` 绑定表，框架通过 `DataManager.get_table(table).load_schema()` 取得表 schema（dict）并注入 Handler，不做单独 data source schema。 |
| **Save** | 当 `context["is_dry_run"]` 为 False 时：先调用用户钩子 `on_before_save(context, normalized_data)`，再由框架将 `normalized_data["data"]` 按表 schema 的 primaryKey 写入绑定表。 |
| **is_dry_run** | 配置：config 顶层 **`"is_dry_run": True`**（bool）。框架在 _preprocess 中将其注入 **`context["is_dry_run"]`**，用户与框架均可读取。为 True 时不执行用户 save 与系统写入。 |
| **Handler 类** | 继承 `BaseHandler`，可覆盖 `on_prepare_context`、`on_before_fetch`、`on_after_mapping`、`on_after_normalize`、`on_before_save` 等钩子；默认管线已包含构建 ApiJob、执行、字段映射、schema 规范化、校验与写入。 |
| **Provider 类** | 继承 `BaseProvider`，定义 `provider_name`、`requires_auth`、`auth_type`、`api_limits`，实现 `_initialize()`；放在 `userspace/data_source/providers/{provider_name}/` 下并由框架发现。 |

---

## 9. 模块索引（按用途）

| 用途 | 类/模块 |
|------|---------|
| 启动一次全量拉取（可写库） | `DataSourceManager.execute()`，且各 handler 的 config 中 `is_dry_run` 为 False 或未配置 |
| 试跑不写库（便于调试） | 在对应 handler 的 config.py 中设置 **`"is_dry_run": True`**；框架会注入到 `context["is_dry_run"]` |
| 实现一个数据源 | 继承 `BaseHandler`，配置 `config.py` + mapping 中的 `handler` |
| 自定义写入（在系统写入前） | 覆盖 `BaseHandler.on_before_save(context, normalized_data)` |
| 实现一个数据供应商 | 继承 `BaseProvider`，实现 `_initialize()`，声明 `api_limits` |
| 配置项访问 | `DataSourceConfig` 的 `get_*` 方法 |
| 单次 API 任务描述 | `ApiJob` |
| 一批 API 任务 | `ApiJobBundle` |
| 执行顺序与依赖注入 | `DataSourceExecutionScheduler.run()` |
| 日期范围与续跑逻辑 | `RenewManager` + config 的 `renew`、`last_update_info`、`result_group_by.by_key` |
