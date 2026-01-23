# BaseHandler 数据流规范

## 概述

本文档明确定义 BaseHandler 的完整数据流，包括每个步骤的输入输出格式、数据转换规则和可用的钩子。

## 执行流程总览

```
execute(global_dependencies)
  ↓
_preprocess(global_dependencies) → List[ApiJob]
  ↓
_executing(apis_jobs) → Dict[str, Any]  # fetched_data
  ↓
_postprocess(fetched_data) → Dict[str, Any]  # normalized_data
  ↓
返回 normalized_data
```

---

## 阶段 1: 预处理阶段 (`_preprocess`)

### 输入

**`global_dependencies: Dict[str, Any]`**
- 全局依赖数据，由 `DataSourceExecutionScheduler` 提供
- 常见依赖：
  - `latest_completed_trading_date: str` - 最新完成交易日（YYYYMMDD）
  - `stock_list: List[Dict[str, Any]]` - 股票列表
  - 其他业务依赖

**`self.context: Dict[str, Any]`**
- 执行上下文，包含：
  - `data_source_name: str` - 数据源名称
  - `schema: DataSourceSchema` - Schema 定义
  - `config: DataSourceConfig` - 配置对象
  - `providers: Dict[str, BaseProvider]` - Provider 实例字典
  - `data_manager: DataManager` - 数据管理器实例

### 处理步骤

#### 1.1 注入全局依赖 (`_inject_required_global_dependencies`)

**输入**: `global_dependencies: Dict[str, Any]`

**输出**: 更新后的 `self.context: Dict[str, Any]`

**行为**: 将全局依赖注入到 `self.context` 中（不覆盖已有键）

---

#### 1.1.5 调用钩子 `on_prepare_context` ⭐ **新增钩子**

**输入**: `self.context: Dict[str, Any]`（已注入全局依赖）

**输出**: `Dict[str, Any]` - 处理后的 context

**默认行为**: 直接返回输入的 `context`（不做任何修改）

**用途**:
- **集中注入派生数据到 context**（推荐用途）
  - 派生字段：`context["last_update"]`、`context["index_map"]` 等
  - 缓存数据：`context["some_cache"]` 等
  - 业务状态：`context["business_state"]` 等
- **避免在各个钩子里零散修改 context**

**调用时机**: 在 `_inject_required_global_dependencies` 之后、`_config_to_api_jobs` 之前

**示例**:

```python
def on_prepare_context(self, context):
    """准备 context，注入派生数据"""
    # 注入 last_update
    context["last_update"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 构建 index_map
    index_list = context.get("index_list", [])
    context["index_map"] = {idx["id"]: idx["name"] for idx in index_list}
    
    # 缓存数据
    data_manager = context.get("data_manager")
    if data_manager:
        context["stock_latest_dates"] = data_manager.stock.kline.load_latest_dates()
    
    return context
```

---

#### 1.2 构建 ApiJob 列表 (`_config_to_api_jobs`)

**输入**: `self.context["config"]` - 配置对象

**输出**: `List[ApiJob]` - ApiJob 列表

**格式说明**:

```python
# 输入：config["apis"]
apis_conf = {
    "api_name1": {
        "provider_name": "tushare",
        "method": "get_xxx",
        "max_per_minute": 200,
        "depends_on": ["other_api"],
        "params": {...},
        "field_mapping": {...},
    },
    "api_name2": {...},
}

# 输出：List[ApiJob]
[
    ApiJob(
        api_name="api_name1",
        provider_name="tushare",
        method="get_xxx",
        params={...},
        depends_on=["other_api"],
        rate_limit=200,
        job_id="api_name1",  # 默认等于 api_name
    ),
    ...
]
```

**转换规则**:
- `api_name` = config key
- `job_id` = `api_name`（默认，可在后续钩子中修改）
- `rate_limit` = `max_per_minute`（默认 50）

---

#### 1.3 计算并注入日期范围 (`_add_date_range_to_api_jobs`)

**输入**: 
- `self.context: Dict[str, Any]`
- `apis: List[ApiJob]`（未注入日期范围）

**输出**: `List[ApiJob]`（已注入日期范围）

**处理逻辑**:

1. **检查显式指定的日期范围**:
   - 如果 `context` 中有 `start_date` 和 `end_date`，直接使用

2. **调用钩子 `on_calculate_date_range`**:
   - 如果返回日期范围，直接使用
   - 返回格式：
     - `None` - 使用默认逻辑
     - `Tuple[str, str]` - 统一日期范围 `(start_date, end_date)`
     - `Dict[str, Tuple[str, str]]` - per stock 日期范围 `{stock_id: (start_date, end_date)}`

3. **默认逻辑**（如果钩子返回 `None`）:
   - 判断目标表是否为空
   - 根据 `renew_mode` 计算日期范围：
     - `incremental`: 从数据库最新日期之后增量补到当前
     - `rolling`: 滚动窗口（`rolling_unit` + `rolling_length`）
     - 其他: 默认日期范围

**输出格式**:

```python
# 每个 ApiJob 的 params 中已注入日期范围
ApiJob(
    api_name="api_name1",
    params={
        "start_date": "20200101",  # YYYYMMDD 格式
        "end_date": "20250123",
        # ... 其他参数
    },
    ...
)
```

---

#### 1.4 调用钩子 `on_before_fetch`

**输入**:
- `self.context: Dict[str, Any]`
- `apis: List[ApiJob]`（已注入日期范围）

**输出**: `List[ApiJob]`（处理后的 ApiJob 列表）

**用途**:
- 调整 ApiJob 参数
- 添加或移除 ApiJob
- 修改 ApiJob 的依赖关系
- **为每个实体（如股票）创建独立的 ApiJob**

**示例**（corporate_finance）:

```python
def on_before_fetch(self, context, apis):
    # 为每个股票创建独立的 ApiJob
    expanded_apis = []
    for stock_id in stock_list:
        new_api = ApiJob(
            api_name="finance_data",
            job_id=f"{stock_id}_finance",  # 修改 job_id
            params={
                **base_api.params,
                "ts_code": stock_id,  # 添加股票参数
            },
        )
        expanded_apis.append(new_api)
    return expanded_apis
```

---

## 阶段 2: 执行阶段 (`_executing`)

### 输入

**`apis_jobs: List[ApiJob]`** - 预处理后的 ApiJob 列表

### 处理步骤

#### 2.1 构建 Job Batch (`_build_api_job_batch_per_stock`)

**输入**: `apis_jobs: List[ApiJob]`

**输出**: `ApiJobBatch` 对象

**格式说明**:

```python
ApiJobBatch(
    batch_id="data_source_name",  # 由 data_source_name 生成
    api_jobs=[...],  # ApiJob 列表
    description="...",
)
```

---

#### 2.2 调用钩子 `on_after_build_job_batch_for_single_stock`

**输入**:
- `self.context: Dict[str, Any]`
- `job_batch: ApiJobBatch`

**输出**: `ApiJobBatch`（处理后的批次）

**用途**: 检查或调整批次配置

---

#### 2.3 执行 Job Batch (`_execute_job_batch_for_single_stock`)

**输入**:
- `self.context: Dict[str, Any]`
- `job_batch: ApiJobBatch`
- `all_apis: List[ApiJob]`

**输出**: `Dict[str, Any]` - `batch_results`

**格式说明**:

```python
# batch_results 格式
batch_results = {
    "job_id1": raw_result1,  # 原始 API 返回结果（DataFrame / list / dict）
    "job_id2": raw_result2,
    ...
}
```

**处理逻辑**:
1. 调用 `ApiJobExecutor.run_batches([job_batch])`
2. 返回 `{batch_id: {job_id: result}}`
3. 提取 `batch_results = exec_result[batch_id]`
4. 对每个 `api_job` 调用 `on_after_execute_single_api_job` 钩子

---

#### 2.4 调用钩子 `on_after_execute_single_api_job`

**输入**:
- `self.context: Dict[str, Any]`
- `api_job: ApiJob`
- `fetched_data: Dict[str, Any]` - `{job_id: result}` 格式（当前单个 job 的结果）

**输出**: `Dict[str, Any]` - 处理后的 `{job_id: result}` 格式

**默认行为**: 直接返回输入的 `fetched_data`（不做任何修改）

**用途**:
- **重组/清洗单个 API 的返回结果**（推荐用途）
  - DataFrame 预处理
  - 字段重命名/过滤
  - 异常值处理
- **可以在执行阶段就保存数据**（如 corporate_finance）
- **吃掉纯依赖 API 的结果**（如果该 API 不对最终 schema 有贡献）

**示例**:

```python
# 示例 1: 清洗单个 API 的结果
def on_after_execute_single_api_job(self, context, api_job, fetched_data):
    result = fetched_data.get(api_job.job_id)
    # 清洗数据
    cleaned_result = self._clean_single_api_result(result)
    return {api_job.job_id: cleaned_result}

# 示例 2: 吃掉纯依赖 API（不对最终 schema 有贡献）
def on_after_execute_single_api_job(self, context, api_job, fetched_data):
    if api_job.api_name == "dependency_only_api":
        # 这个 API 只是给其他 API 提供依赖，不进入最终结果
        # 可以在这里使用它的结果，然后返回空字典
        dependency_data = fetched_data.get(api_job.job_id)
        context["dependency_cache"] = dependency_data  # 存到 context 供后续使用
        return {}  # 不保留在 fetched_data 中
    return fetched_data  # 其他 API 原样返回

# 示例 3: 执行阶段保存数据（corporate_finance）
def on_after_execute_single_api_job(self, context, api_job, fetched_data):
    result = fetched_data.get(api_job.job_id)
    # 标准化并保存
    normalized = self._normalize_single_stock_data(context, result, api_job)
    data_manager.stock.corporate_finance.save_batch(normalized["data"])
    return fetched_data  # 仍然返回，让 on_after_fetch 统一格式
```

---

#### 2.5 调用钩子 `on_after_execute_job_batch_for_single_stock`

**输入**:
- `self.context: Dict[str, Any]`
- `job_batch: ApiJobBatch`
- `fetched_data: Dict[str, Any]` - `{job_id: result}` 格式（整个批次的结果）

**输出**: `Dict[str, Any]` - 处理后的 `{job_id: result}` 格式

**默认行为**: 直接返回输入的 `fetched_data`（不做任何修改）

**重要设计原则** ⚠️:

- **BaseHandler 不会自动筛选/删除 API 结果**
- **所有 API 的结果都会传递到后续钩子**（包括纯依赖 API）
- **这样设计的好处**:
  - ✅ **方便调试**: 可以在 `on_after_fetch` 中看到所有 API 的原始返回
  - ✅ **灵活性高**: Handler 可以自己决定如何处理每个 API
  - ✅ **信息完整**: 不会丢失任何执行信息

**用途**:
- **重组/精简整个批次的 fetched_data**（可选）
  - 合并多个 API 的结果
  - 丢弃不需要的中间结果（如果 handler 自己决定）
  - 精简数据结构
- **可以在执行阶段就保存数据**（如 kline、adj_factor_event）

**示例**:

```python
# 示例 1: 合并多个 API 的结果（可选）
def on_after_execute_job_batch_for_single_stock(self, context, job_batch, fetched_data):
    # 合并 A, B, C 三个 API 的结果
    merged_result = self._merge_api_results(
        fetched_data.get("job_A"),
        fetched_data.get("job_B"),
        fetched_data.get("job_C"),
    )
    # 返回合并后的结果，丢弃原始的 A, B, C
    return {"merged_job": merged_result}

# 示例 2: 执行阶段保存数据（kline）
def on_after_execute_job_batch_for_single_stock(self, context, job_batch, fetched_data):
    # 按股票分组处理并保存
    stock_data_map = self._process_fetched_data_by_stock(fetched_data, job_batch.api_jobs)
    for stock_id, records in stock_data_map.items():
        data_manager.stock.kline.save(records)
    return fetched_data  # 仍然返回所有结果，让 on_after_fetch 统一格式
```

---

#### 2.6 调用钩子 `on_after_fetch` ⭐ **关键钩子**

**输入**:
- `self.context: Dict[str, Any]`
- `fetched_data: Dict[str, Any]` - `{job_id: result}` 格式（执行层原始输出，可能已被前面的钩子处理）
- `apis: List[ApiJob]` - 执行的 ApiJob 列表

**输出**: `Dict[str, Any]` - **统一格式的 fetched_data**

**默认行为**: 直接返回输入的 `fetched_data`（不做任何转换）

**统一格式规范** ⭐:

```python
fetched_data = {
    api_name: {
        "_unified": raw_result,  # 全局数据（无 entity 维度）
        entity_id1: raw_result,  # 按 entity 分组的数据
        entity_id2: raw_result,
        # ...
    }
}
```

**格式说明**:

1. **外层 key**: `api_name`（与 `config["apis"]` 中的 key 一致）
2. **内层 key**: 
   - `"_unified"`: 表示全局数据，不需要按 entity 分组
   - `entity_id`: 表示按某个实体分组的数据（如 `stock_id`、`index_id` 等）
3. **value**: `raw_result` - 原始结果（可以是 DataFrame、list[dict] 等）

**转换职责**:

所有 handler 的 `on_after_fetch` **应该**将 `{job_id: result}` 转换为统一格式。

**重要设计原则** ⚠️:

- **BaseHandler 不会自动筛选/删除 API 结果**
- **`on_after_fetch` 会收到所有 API 的结果**（包括纯依赖 API，如 A）
- **Handler 可以自己决定如何处理每个 API**:
  - 如果某个 API 不对最终 schema 有贡献，可以在 `on_after_fetch` 中不转换它（不放入统一格式）
  - 或者转换为统一格式但配置空的 field_mapping（让 normalize 阶段自动过滤）
- **这样设计的好处**:
  - ✅ **方便调试**: 可以看到所有 API 的原始返回
  - ✅ **灵活性高**: Handler 完全控制哪些 API 进入 normalize 阶段
  - ✅ **信息完整**: 不会丢失任何执行信息

**默认规则说明**:

- **基类默认实现**: 直接返回 `{job_id: result}`（不做转换）
- **统一格式规范**: 我们希望所有 handler 都返回统一格式，但这需要 handler 自己实现转换
- **简单 handler**: 如果不实现 `on_after_fetch`，基类的 `_normalize_data` 仍然可以工作（向后兼容），但建议实现统一格式转换

**示例**:

```python
# 简单 handler（shibor）
def on_after_fetch(self, context, fetched_data, apis):
    return {
        "shibor": {
            "_unified": fetched_data.get("shibor")  # 或从 job_id 解析
        }
    }

# 按股票分组（corporate_finance）
def on_after_fetch(self, context, fetched_data, apis):
    result = {}
    for job_id, raw_result in fetched_data.items():
        stock_id = job_id.replace("_finance", "")
        if "finance_data" not in result:
            result["finance_data"] = {}
        result["finance_data"][stock_id] = raw_result
    return result

# 多 API（kline）
def on_after_fetch(self, context, fetched_data, apis):
    result = {}
    for job_id, raw_result in fetched_data.items():
        # 解析 job_id: "kline_000001_daily" -> api_name="daily_kline", stock_id="000001"
        parts = job_id.split("_")
        stock_id = parts[1]
        api_name = f"{parts[2]}_kline" if parts[2] != "daily_basic" else "daily_basic"
        
        if api_name not in result:
            result[api_name] = {}
        result[api_name][stock_id] = raw_result
    return result
```

**处理 API 依赖关系**:

当有 API 依赖关系时（如 `B, C` 依赖 `A`），有两种情况：

**情况 1: A 的结果也要进 schema（对最终数据有贡献）**

```python
# 执行层输出（on_after_fetch 会收到）
fetched_data = {
    "job_A": raw_A,
    "job_B": raw_B,
    "job_C": raw_C,
}

# on_after_fetch 转换为统一格式（A 也要进 schema）
return {
    "A": {
        "_unified": raw_A,  # A 也要进 schema
    },
    "B": {
        "_unified": raw_B,
    },
    "C": {
        "_unified": raw_C,
    },
}
```

**情况 2: A 是纯依赖 API（不对最终 schema 有贡献）**

**重要**: BaseHandler **不会自动删除 A 的结果**，A 的结果会出现在 `on_after_fetch` 的参数中。

**推荐做法**: 在 `on_after_fetch` 中自己决定是否转换 A

```python
def on_after_fetch(self, context, fetched_data, apis):
    """
    on_after_fetch 会收到所有 API 的结果（包括 A）
    但我们可以自己决定是否转换 A
    """
    result = {}
    
    # 转换 B 和 C（对 schema 有贡献）
    if "job_B" in fetched_data:
        result["B"] = {"_unified": fetched_data.get("job_B")}
    if "job_C" in fetched_data:
        result["C"] = {"_unified": fetched_data.get("job_C")}
    
    # A 是纯依赖 API，不对最终 schema 有贡献
    # 可以选择不转换它（不放入统一格式）
    # 但它的原始结果仍然在 fetched_data 中，方便调试
    
    # 可选：如果需要使用 A 的结果 enrich B/C，可以在这里处理
    raw_A = fetched_data.get("job_A")
    if raw_A:
        # 使用 A 的结果 enrich B/C（如果需要）
        pass
    
    return result  # 只包含 B 和 C，不包含 A
```

**设计优势**:

- ✅ **方便调试**: 即使 A 不对最终结果有贡献，它的结果仍然在 `fetched_data` 中，可以查看
- ✅ **灵活性高**: Handler 可以自己决定如何处理每个 API
- ✅ **信息完整**: 不会丢失任何执行信息

**默认规则总结**:

1. **执行层输出**: `{job_id: result}` - 所有 API 的结果都包含在内
2. **钩子处理**:
   - `on_after_execute_single_api_job`: 可以清洗/重组单个 API 的结果，或吃掉纯依赖 API
   - `on_after_execute_job_batch_for_single_entity`: 可以重组/精简整个批次，或吃掉纯依赖 API
3. **统一格式转换（基类内置）**:
   - `on_after_fetch` 会根据 `config.apis[api_name].group_by` 自动将 `{job_id: result}` 转换为
     统一格式 `{api_name: {entity_id_or_unified: raw_result}}`；
   - 如果所有 API 都未配置 `group_by`，则按 api_name 聚合到 `_unified`；
   - 如果至少一个 API 配置了 `group_by`，则按实体分组（找不到实体 ID 时回退 `_unified`）。
4. **默认行为**: 如果 handler 不实现这些钩子，基类仍然会：
   - 执行所有 API；
   - 使用默认的 `on_after_fetch` 生成统一格式的 `fetched_data`；
   - 使用默认的 `_normalize_data` 完成标准化流程。

## 默认规则 vs 统一格式规范

### 默认规则（基类实现）

**基类的默认实现（当前设计，BREAKING）**：

1. **`on_after_fetch` 默认行为**: 不再是简单透传，而是统一转换为规范格式：

   ```python
   def on_after_fetch(self, context, fetched_data, apis):
       """
       默认行为：在编排层先判断是否存在 group_by 配置：
       - 如果至少有一个 API 配置了 group_by，则调用
         DataSourceHandlerHelper.build_grouped_fetched_data；
       - 否则调用 DataSourceHandlerHelper.build_unified_fetched_data。
       """
       if DataSourceHandlerHelper.has_group_by_config(context, apis):
           return DataSourceHandlerHelper.build_grouped_fetched_data(context, fetched_data, apis)
       return DataSourceHandlerHelper.build_unified_fetched_data(context, fetched_data, apis)
   ```

2. **`_normalize_data` 默认行为**: 假定 `fetched_data` 已经是统一格式：

   - 即 `{api_name: {entity_id_or_unified: raw_result}}`；
   - 所有 normalize 相关 helper（包括 `extract_mapped_records`）也只支持该格式。

### 统一格式规范（推荐做法）

**我们希望所有 handler 都遵循统一格式**：

```python
fetched_data = {
    api_name: {
        "_unified": raw_result,  # 或
        entity_id: raw_result,
    }
}
```

**并且现在由基类的 `on_after_fetch` 默认实现来完成转换**，大部分 handler 无需关心。

### 总结

- **默认规则**: 基类会自动将 `{job_id: result}` 转换为统一格式，规则由 `group_by` 控制；
- **统一格式规范**: 所有后续流程（normalize、mapping 等）都只认统一格式；
- **向后兼容**: 旧的 `{job_id: result}` / `{api_name: result}` 视为废弃格式，不再推荐使用，
  需要升级到统一规范。

---

## API 依赖关系的处理

### 场景：3 个 API，B 和 C 依赖 A

**执行层输出**（`batch_results`）:

```python
{
    "job_A": raw_A,  # A 先执行
    "job_B": raw_B,  # B 依赖 A，使用 A 的结果
    "job_C": raw_C,  # C 依赖 A，使用 A 的结果
}
```

### 情况 1: A 的结果也要进 schema（对最终数据有贡献）

**处理方式**: A 的结果也要进入统一格式

```python
# on_after_fetch 转换为统一格式
fetched_data = {
    "A": {
        "_unified": raw_A,  # A 也要进 schema
    },
    "B": {
        "_unified": raw_B,
    },
    "C": {
        "_unified": raw_C,
    },
}
```

**后续处理**: `_normalize_data` 会对 A、B、C 都应用 field_mapping，合并到最终结果中

### 情况 2: A 是纯依赖 API（不对最终 schema 有贡献）

**推荐做法**: 在 `on_after_execute_job_batch_for_single_stock` 中吃掉 A 的结果

```python
def on_after_execute_job_batch_for_single_stock(self, context, job_batch, fetched_data):
    """
    吃掉纯依赖 API A 的结果，只保留 B 和 C
    """
    raw_A = fetched_data.get("job_A")
    
    # 使用 A 的结果 enrich B, C（如果需要）
    enriched_B = self._enrich_with_A(fetched_data.get("job_B"), raw_A)
    enriched_C = self._enrich_with_A(fetched_data.get("job_C"), raw_A)
    
    # 返回处理后的结果，不包含 A
    return {
        "job_B": enriched_B,
        "job_C": enriched_C,
        # 没有 "job_A"
    }

# 然后在 on_after_fetch 中转换为统一格式
def on_after_fetch(self, context, fetched_data, apis):
    """
    转换为统一格式，此时 fetched_data 已经不包含 A 了
    """
    return {
        "B": {
            "_unified": fetched_data.get("job_B"),
        },
        "C": {
            "_unified": fetched_data.get("job_C"),
        },
        # 没有 "A"
    }
```

**为什么推荐在钩子里吃掉**:

1. ✅ **语义清晰**: 明确表示 A 只是中间结果，不对最终数据有贡献
2. ✅ **减少数据量**: 不进入 normalize 阶段，减少内存和处理时间
3. ✅ **避免混淆**: normalize 阶段只看"真正要进 schema 的 API"

**次优做法**: 保留 A 但配置空的 field_mapping

```python
# config.json
{
    "apis": {
        "A": {
            "field_mapping": {},  # 空映射，不会产生任何记录
            ...
        },
        "B": {...},
        "C": {...},
    }
}
```

这种方式可以工作，但**不推荐**，因为：
- ❌ 语义不清晰（A 明明不对 schema 有贡献，却出现在 fetched_data 中）
- ❌ 浪费内存和处理时间

---

## 默认规则总结

1. **执行层输出**: `{job_id: result}` - 所有 API 的结果都包含在内（包括纯依赖 API）

2. **钩子处理**（可选）:
   - `on_after_execute_single_api_job`: 可以清洗/重组单个 API 的结果
   - `on_after_execute_job_batch_for_single_stock`: 可以重组/精简整个批次
   - **重要**: BaseHandler **不会自动删除任何 API 的结果**

3. **统一格式转换**（推荐）: `on_after_fetch` 将 `{job_id: result}` 转换为 `{api_name: {entity_id: result}}`
   - **默认行为**: 如果不实现，基类直接返回 `{job_id: result}`（向后兼容，但可能有问题）
   - **推荐做法**: 实现转换，返回统一格式
   - **重要**: `on_after_fetch` **会收到所有 API 的结果**（包括纯依赖 API），Handler 可以自己决定是否转换它们

4. **Normalize 阶段**: 只处理统一格式中的 API
   - 如果某个 API 不在统一格式中（如纯依赖 API A），它不会进入 normalize 阶段
   - 如果某个 API 在统一格式中但配置了空的 field_mapping，它也不会产生记录

---

## 阶段 3: 后处理阶段 (`_postprocess`)

### 输入

**`fetched_data: Dict[str, Any]`** - 统一格式的 fetched_data（`on_after_fetch` 的输出）

### 处理步骤

#### 3.1 标准化数据 (`_normalize_data`) ⚠️ **私有方法，不暴露为钩子**

**输入**: 
- `self.context: Dict[str, Any]`
- `fetched_data: Dict[str, Any]` - **统一格式**

**输出**: `Dict[str, Any]` - `normalized_data`

**格式说明**:

```python
normalized_data = {
    "data": [
        {field1: value1, field2: value2, ...},  # 已应用 schema 的记录
        ...
    ]
}
```

**处理步骤**:

1. **解析配置和 schema**:
   ```python
   apis_conf = context["config"].get_apis()
   schema = context["schema"]
   ```

2. **字段覆盖校验**:
   - 检查哪些 schema 字段在 field_mapping 中没有被覆盖（仅日志提醒）

3. **提取并映射记录** (`DataSourceHandlerHelper.extract_mapped_records`):
   ```python
   # 遍历每个 api_name
   for api_name, api_cfg in apis_conf.items():
       api_data = fetched_data.get(api_name)  # {entity_id: raw_result} 或 {"_unified": raw_result}
       
       # 遍历每个 entity_id（包括 _unified）
       for entity_id, raw_result in api_data.items():
           records = result_to_records(raw_result)
           mapped = apply_field_mapping(records, api_cfg["field_mapping"])
           mapped_records.extend(mapped)
   ```

4. **调用钩子 `on_after_mapping`**:
   - 输入: `mapped_records: List[Dict[str, Any]]`（已应用 field_mapping）
   - 输出: `List[Dict[str, Any]]`（处理后的记录列表）

5. **应用 schema** (`DataSourceHandlerHelper.apply_schema`):
   - 只保留 schema 定义的字段
   - 类型转换和默认值填充

6. **包装返回** (`DataSourceHandlerHelper.build_normalized_payload`):
   ```python
   return {"data": normalized_records}
   ```

**默认行为**:
- 80% 的 handler 不需要复写此方法
- 复杂场景（如 kline 需要合并多个 API）可以通过钩子自定义

---

#### 3.2 调用钩子 `on_after_mapping`

**输入**:
- `self.context: Dict[str, Any]`
- `mapped_records: List[Dict[str, Any]]` - 已应用 field_mapping 的记录列表

**输出**: `List[Dict[str, Any]]` - 处理后的记录列表

**用途**:
- 从 context 添加字段（如 `last_update`、`is_active`）
- 过滤记录（如只保留有效的记录）
- 数据转换（如日期格式标准化）
- 添加计算字段

**示例**:

```python
def on_after_mapping(self, context, mapped_records):
    # 添加 last_update 字段
    last_update = context.get("last_update", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    for record in mapped_records:
        record["last_update"] = last_update
        record["is_active"] = 1
    
    # 过滤无效记录
    return [r for r in mapped_records if r.get("id") and r.get("name")]
```

---

#### 3.3 调用钩子 `on_after_normalize`

**输入**:
- `self.context: Dict[str, Any]`
- `normalized_data: Dict[str, Any]` - `{"data": [...]}` 格式

**输出**: `Dict[str, Any]` - 处理后的 normalized_data

**用途**:
- **保存数据到数据库**（最常见）
- 数据后处理（如 CSV 导出）
- 日志记录

**示例**:

```python
def on_after_normalize(self, context, normalized_data):
    data_manager = context.get("data_manager")
    if not data_manager:
        return normalized_data
    
    if context.get('dry_run', False):
        return normalized_data
    
    data_list = normalized_data.get("data", [])
    if not data_list:
        return normalized_data
    
    # 清理 NaN
    from core.infra.db.helpers.db_helpers import DBHelper
    data_list = DBHelper.clean_nan_in_list(data_list, default=0.0)
    
    # 保存数据
    count = data_manager.stock.list.save(data_list)
    logger.info(f"✅ 保存数据完成，共 {count} 条记录")
    
    return normalized_data
```

---

#### 3.4 验证标准化数据 (`_validate_normalized_data`)

**输入**: `normalized_data: Dict[str, Any]`

**输出**: `Dict[str, Any]`（如果验证失败会抛出异常）

**行为**: 验证标准化后的数据是否符合 schema

---

## 数据格式总结

### 1. 执行层输出 (`batch_results`)

```python
{
    "job_id1": raw_result1,  # DataFrame / list[dict] / dict
    "job_id2": raw_result2,
    ...
}
```

### 2. 统一格式 (`on_after_fetch` 输出)

```python
{
    api_name: {
        "_unified": raw_result,  # 全局数据
        entity_id1: raw_result,  # 按 entity 分组
        entity_id2: raw_result,
    }
}
```

### 3. 标准化输出 (`normalized_data`)

```python
{
    "data": [
        {field1: value1, field2: value2, ...},  # 已应用 schema
        ...
    ]
}
```

---

## 钩子总结

### 可用的钩子（按调用顺序）

1. **`on_prepare_context`** ⭐ **新增** - 准备 context，注入派生数据
2. **`on_calculate_date_range`** - 自定义日期范围计算
3. **`on_before_fetch`** - 调整 ApiJobs（添加/移除/修改）
4. **`on_after_build_job_batch_for_single_stock`** - 调整批次配置
5. **`on_after_execute_single_api_job`** ⭐ **修改** - 单个 job 执行后处理，返回处理后的 `{job_id: result}`
6. **`on_after_execute_job_batch_for_single_stock`** ⭐ **修改** - 批次执行后处理，返回处理后的 `{job_id: result}`
7. **`on_after_fetch`** ⭐ - **将 `{job_id: result}` 转换为统一格式**
8. **`on_after_mapping`** - 字段映射后的自定义处理
9. **`on_after_normalize`** - 标准化后的处理（通常用于保存数据）
10. **`on_error`** - 错误处理

### 私有方法（不暴露为钩子）

- `_normalize_data` - 标准化数据（私有方法，不暴露）
- `_validate_normalized_data` - 验证数据（私有方法，不暴露）

---

## 设计原则

1. **统一格式规范**: 所有 handler 的 `fetched_data` 必须遵循统一格式
2. **默认流程**: 80% 的 handler 不需要复写 `_normalize_data`
3. **钩子扩展**: 复杂场景通过钩子自定义，简单场景用默认流程
4. **私有方法保护**: `_normalize_data` 是私有方法，不暴露为钩子

---

## 示例流程

### 简单 Handler（shibor）

```
1. _preprocess
   → on_before_fetch: 返回原始 apis（无需修改）

2. _executing
   → batch_results: {"shibor": DataFrame}
   → on_after_fetch: 转换为统一格式
     {
       "shibor": {
         "_unified": DataFrame
       }
     }

3. _postprocess
   → _normalize_data: 默认流程处理
   → on_after_mapping: 无需处理
   → on_after_normalize: 保存数据
```

### 复杂 Handler（corporate_finance）

```
1. _preprocess
   → on_before_fetch: 为每个股票创建 ApiJob
     [
       ApiJob(job_id="000001_finance", ...),
       ApiJob(job_id="000002_finance", ...),
     ]

2. _executing
   → batch_results: {
       "000001_finance": DataFrame,
       "000002_finance": DataFrame,
     }
   → on_after_execute_single_api_job: 每个股票执行后立即保存
   → on_after_fetch: 转换为统一格式（虽然数据已保存，但格式要统一）
     {
       "finance_data": {
         "000001.SH": DataFrame,
         "000002.SH": DataFrame,
       }
     }

3. _postprocess
   → _normalize_data: 返回空数据（因为已保存）
   → on_after_normalize: 只做日志
```

---

## 总结

**关键点**:

1. ✅ **统一格式规范**: `on_after_fetch` 必须返回统一格式
2. ✅ **默认 normalize 流程**: 80% 的 handler 不需要复写 `_normalize_data`
3. ✅ **钩子扩展**: 复杂场景通过钩子自定义
4. ✅ **私有方法保护**: `_normalize_data` 不暴露为钩子

**数据流**:

```
{job_id: result} → on_after_fetch → {api_name: {entity_id: result}} → _normalize_data → {data: [...]}
```
