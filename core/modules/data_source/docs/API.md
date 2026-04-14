# Data Source 模块 API 文档

**版本：** `0.2.0`

本文档采用统一 API 条目格式。`BaseHandler` 除 **`execute`** 外还有大量内部阶段方法与钩子，**以 `base_class/base_handler.py` 为准**；此处只列对外主入口与数据类。

---

## DataSourceManager

### 函数名
`__init__(self, is_verbose: bool = False) -> None`

- 状态：`stable`
- 描述：创建管理器；持有执行调度器与配置/handler 解析缓存。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `is_verbose` (可选) | `bool` | 详细日志（兼容保留） |

- 返回值：`None`

---

### 函数名
`execute(self) -> None`

- 状态：`stable`
- 描述：刷新缓存 → 发现 mapping 与 Provider → 为每个 **启用** data source 构建 **Handler** → **`DataSourceExecutionScheduler.run`**。是否写库由 config **`is_dry_run`** 控制。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

## BaseHandler

### 函数名
`execute(self, dependencies_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

- 状态：`stable`
- 描述：Handler **同步主入口**：注入依赖数据、**`on_before_run`** 短路、预处理、API 执行、标准化、校验与保存（非 dry-run）。返回标准化结果字典（具体键以子类为准）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `dependencies_data` (可选) | `Optional[Dict[str, Any]]` | 上游已执行数据源产出，供依赖注入 |

- 返回值：`Dict[str, Any]`

---

### 函数名
`get_key(self) -> Optional[str]`

- 状态：`stable`
- 描述：当前 **data source key**（mapping 中的键，非表名）。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`Optional[str]`

---

### 函数名
`__init__(self, data_source_key: str, schema: Any, config: DataSourceConfig, providers: Dict[str, BaseProvider], depend_on_data_source_names: List[str] = None) -> None`

- 状态：`stable`
- 描述：构造上下文（含 **`DataManager.get_instance()`**、providers、config、schema）。
- 诞生版本：`0.2.0`
- params：见签名；`depend_on_data_source_names` 可省略（默认 `[]`）。

- 返回值：`None`

---

## BaseProvider

子类须定义类属性 **`provider_name`**；若 **`requires_auth`** 则按 **`auth_type`** 校验 **`config`**（见 `base_provider.py`）。**`api_limits`** 为声明式限流（由执行层消费）。抽象 API 方法由子类实现。

---

## ApiJob

### 函数名
`__init__(self, api_name: Optional[str] = None, provider_name: Optional[str] = None, method: Optional[str] = None, params: Optional[Dict[str, Any]] = None, api_params: Optional[Dict[str, Any]] = None, depends_on: Optional[List[str]] = None, rate_limit: int = 0, job_id: Optional[str] = None) -> None`

- 状态：`stable`
- 描述：单次 API 调用描述载体；**`execute()`** 在本类中为占位，由执行器调用 Provider。
- 诞生版本：`0.2.0`
- params：见 `data_class/api_job.py` 字段说明。
- 返回值：`None`

---

## ApiJobBundle

**`@dataclass`**：`bundle_id: str`，**`apis: List[ApiJob]`**，可选 **`tuple_order_map`**、**`start_date`**、**`end_date`**。静态方法 **`to_id(data_source_key: str) -> str`** 生成批次 id。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
