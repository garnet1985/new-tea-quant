# Data Source 架构文档

**版本：** 3.0  
**日期：** 2026-01-XX  
**状态：** 生产环境

---

## 📋 目录

1. [设计背景](#设计背景)
2. [核心设计思想](#核心设计思想)
3. [架构设计](#架构设计)
4. [Entity 职责与对应关系](#entity-职责与对应关系)
5. [运行时 Workflow](#运行时-workflow)
6. [数据流设计](#数据流设计)
7. [重要决策记录 (Decisions)](#重要决策记录-decisions)
8. [版本历史](#版本历史)

---

## 设计背景

### 问题背景

在重构数据源模块之前，存在以下问题：

1. **硬编码的数据获取逻辑**：每个数据源的获取逻辑都硬编码在 `DataSourceManager` 中，难以扩展和维护
2. **重复的依赖获取**：`latest_completed_trading_date` 和 `stock_list` 在多个 handler 中重复获取，可能导致数据不一致
3. **缺乏统一的数据格式**：不同数据源返回的数据格式不统一，难以统一处理
4. **难以切换数据源**：要切换数据源（如从 Tushare 切换到 AKShare），需要修改代码
5. **API 限流管理混乱**：限流逻辑分散在各个 handler 中，难以统一管理

### 设计目标

1. **配置驱动**：通过 `mapping.json` 配置 handler 的启用、依赖和参数，无需修改代码
2. **统一依赖管理**：在 `renew_data` 开始时统一解析和获取所有需要的全局依赖
3. **按需获取**：只获取真正需要的依赖，避免不必要的开销
4. **易于扩展**：预留接口，方便未来添加新的全局依赖和数据源
5. **职责清晰**：每层各司其职，Provider 负责 API 封装，Handler 负责业务逻辑，Manager 负责协调管理

---

## 核心设计思想

### 1. 框架定义准则，用户控制实现

```python
# 框架：定义 dataSource 和 schema
KLINE = DataSourceSchema(
    name="kline",
    schema={...}
)

# 用户：根据手里的 Provider 自由实现 Handler
class MyHandler(BaseDataSourceHandler):
    data_source = "kline"
    
    async def fetch(self, context):
        # 完全由用户控制
        return {...}
```

### 2. 一个 dataSource，多个 handler（但运行时只选一个）

```python
# 可以有多个 handler 实现（不同实现方式）
# - handlers.kline.KlineHandler
# - userspace/data_source/handlers/kline.MyKlineHandler

# 通过 mapping.json 选择使用哪个
# ⚠️ 重要：运行时只能选择一个 handler，不能同时运行多个 handler
# 同时运行多个 handler 会导致数据互相覆盖，可能引起灾难性后果
{
    "kline": {
        "handler": "handlers.kline.KlineHandler"
    }
}
```

### 3. 配置驱动，灵活切换

```json
{
  "data_sources": {
    "kline": {
      "handler": "handlers.kline.KlineHandler",
      "is_enabled": true,
      "dependencies": {
        "latest_completed_trading_date": true,
        "stock_list": true
      },
      "handler_config": {
        "renew_mode": "incremental"
      }
    }
  }
}
```

---

## 架构设计

### 三层架构

```
┌─────────────────────────────────────────────────┐
│         DataSourceManager (协调层)               │
│  - 加载配置和注册                                 │
│  - 全局依赖注入                                   │
│  - 运行所有 enabled 的 handler                    │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │   Handler (业务层)  │
         │  - 数据获取逻辑      │
         │  - 数据标准化        │
         │  - 多 Provider 组合  │
         │  - 依赖处理          │
         └─────────┬───────────┘
                   │
         ┌─────────▼──────────┐
         │  Provider (基础层)  │
         │  - 纯 API 封装       │
         │  - 认证配置          │
         │  - API 元数据声明    │
         │  - 错误转换          │
         └─────────────────────┘
```

### 详细职责分配

#### Provider 层（基础设施）

**应该包含：**
- ✅ 纯粹的 API 调用方法
- ✅ 认证配置（token, api_key）
- ✅ **API 限流信息声明**（每个 API 的限流）
- ✅ 错误处理和转换（统一错误格式）
- ✅ Provider 元数据

**不应包含：**
- ❌ 业务逻辑
- ❌ 数据标准化
- ❌ 限流执行逻辑
- ❌ 多线程调度

#### Handler 层（业务逻辑）

**应该包含：**
- ✅ 数据获取逻辑（调用 Provider）
- ✅ 数据标准化（转为框架 schema）
- ✅ 多 Provider 组合和协调
- ✅ 依赖数据处理
- ✅ 批量处理逻辑
- ✅ Handler 元信息（dependencies）

**不应包含：**
- ❌ 多线程调度（由 Manager 负责）
- ❌ 全局限流管理（由 TaskExecutor 负责）

#### Manager 层（协调管理）

**应该包含：**
- ✅ 配置加载和 Handler 注册
- ✅ 全局依赖解析和注入
- ✅ 运行所有 enabled 的 handler
- ✅ 进度跟踪
- ✅ 错误汇总

**不应包含：**
- ❌ 具体的数据获取逻辑
- ❌ 数据标准化逻辑
- ❌ 依赖处理（Handler 自己解决）
- ❌ 限流执行（Handler 自己负责）

---

## Entity 职责与对应关系

### Entity 关系图

```
┌─────────────────────────────────────────────────────────────┐
│                    DataSourceManager                         │
│  - 加载配置和注册                                             │
│  - 全局依赖注入                                               │
│  - 运行所有 enabled 的 handler                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │   BaseDataSourceHandler     │
         │  - 数据获取逻辑               │
         │  - 数据标准化                 │
         │  - 多 Provider 组合           │
         │  - 依赖处理                   │
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │      DataSourceTask          │
         │  - 业务任务（包含多个 ApiJob）│
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │         ApiJob              │
         │  - 单个 API 调用任务          │
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │      TaskExecutor           │
         │  - 执行 Tasks               │
         │  - 限流控制                 │
         │  - 并发管理                 │
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │      BaseProvider          │
         │  - 纯 API 封装              │
         │  - 认证配置                 │
         │  - API 元数据声明           │
         └───────────────────────────┘
```

### 详细 Entity 职责

#### 1. DataSourceManager（数据源管理器）

**职责：**
- ✅ 加载 Schema 定义（`_load_schemas()`）
- ✅ 加载 Handler 映射配置（`_load_mapping()`）
- ✅ 动态加载 Handler 类（`_load_handlers()`）
- ✅ 执行数据获取（`renew_data()`）
- ✅ 管理全局依赖注入（`latest_completed_trading_date`、`stock_list` 等）
- ✅ 测试单个 Handler（`fetch()`）

**对应关系：**
- 管理多个 `BaseDataSourceHandler` 实例
- 通过 `DataManager` 访问数据库
- 通过 `ConfigManager` 和 `PathManager` 加载配置

---

#### 2. DataSourceSchema（数据格式规范）

**职责：**
- ✅ 定义数据结构、字段、类型
- ✅ 验证数据是否符合要求（`validate()`）
- ✅ 保证数据一致性

**对应关系：**
- 一个 `DataSourceSchema` 对应一个 data source（1:1）
- 被 `BaseDataSourceHandler` 使用，作为 `normalize()` 的输出标准

---

#### 3. BaseDataSourceHandler（Handler 基类）

**职责：**
- ✅ 定义 Handler 生命周期钩子
- ✅ 提供模板方法 `execute()` 执行完整流程
- ✅ 管理 Provider 实例（通过 `ProviderInstancePool`）
- ✅ 数据获取逻辑（`fetch()`）
- ✅ 数据标准化（`normalize()`）
- ✅ 多 Provider 组合和协调
- ✅ 依赖数据处理
- ✅ 批量处理逻辑

**生命周期钩子：**
- `before_fetch(context)` - 数据准备阶段，构建执行上下文
- `fetch(context)` - 生成 Tasks（包含多个 ApiJobs）
- `after_fetch(tasks, context)` - Tasks 生成后（还未执行）
- `before_all_tasks_execute(tasks, context)` - 所有 tasks 执行前
- `before_single_task_execute(task, context)` - 单个 task 执行前
- `after_single_task_execute(task_id, task_result, context)` - 单个 task 执行后
- `after_all_tasks_execute(task_results, context)` - 所有 tasks 执行后
- `before_normalize(raw_data)` - 标准化前
- `normalize(raw_data)` - 标准化数据
- `after_normalize(normalized_data, context)` - 标准化后，通常用于保存数据
- `on_error(error, context)` - 错误处理

---

#### 4. DataSourceTask（业务任务）

**职责：**
- ✅ 封装一个业务任务（包含多个 ApiJobs）
- ✅ 提供任务元信息（task_id, description）

**对应关系：**
- 由 `BaseDataSourceHandler.fetch()` 生成
- 包含多个 `ApiJob` 实例
- 被 `TaskExecutor` 执行

---

#### 5. ApiJob（API 调用任务）

**职责：**
- ✅ 封装单个 API 调用所需的所有信息
- ✅ 定义依赖关系（`depends_on`）

**对应关系：**
- 由 `BaseDataSourceHandler.fetch()` 生成
- 属于某个 `DataSourceTask`
- 被 `TaskExecutor` 执行
- 调用 `BaseProvider` 的方法

---

#### 6. TaskExecutor（任务执行器）

**职责：**
- ✅ 执行 `DataSourceTask` 列表
- ✅ 拓扑排序（根据 `depends_on`）
- ✅ 限流控制（通过 `RateLimiter`）
- ✅ 并发管理（多线程执行）
- ✅ 错误处理和重试

**对应关系：**
- 执行 `DataSourceTask` 列表
- 调用 `BaseProvider` 的方法
- 使用 `ProviderInstancePool` 获取 Provider 实例
- 返回原始数据给 Handler

---

#### 7. BaseProvider（Provider 基类）

**职责：**
- ✅ 封装第三方 API 调用
- ✅ 声明 API 限流信息（不执行）
- ✅ 认证配置和验证
- ✅ 错误转换（统一错误格式）

**对应关系：**
- 被 `BaseDataSourceHandler` 使用
- 被 `TaskExecutor` 调用
- 通过 `ProviderInstancePool` 管理实例

---

## 运行时 Workflow

### renew_data() 完整执行流程

```
┌─────────────────────────────────────────────────────────────┐
│  DataSourceManager.renew_data()                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  Step 1: 依赖解析 (Dependency Resolution)           │
         │  - 读取 mapping.json，找出所有 is_enabled=true 的    │
         │    handler                                           │
         │  - 收集每个 handler 声明的依赖需求（dependencies）  │
         │  - 去重，得到需要获取的全局依赖列表                 │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  Step 2: 依赖注入 (Dependency Injection)           │
         │  - 根据依赖列表，获取所有需要的全局依赖             │
         │  - 构建 shared_context（包含：                      │
         │    - latest_completed_trading_date                  │
         │    - stock_list                                     │
         │    - test_mode, dry_run 等参数）                    │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  Step 3: Handler 执行循环                           │
         │  遍历所有启用的 handler：                            │
         │                                                     │
         │  for handler_name, handler in enabled_handlers:     │
         │      handler_context = shared_context.copy()        │
         │      await handler.execute(handler_context)        │
         └─────────────┬──────────────────────────────────────┘
                       │
                       │ 进入 Handler.execute() 流程
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  Handler.execute(context)                           │
         │                                                     │
         │  ┌─────────────────────────────────────────────┐   │
         │  │ Phase 1: 数据准备阶段                        │   │
         │  │ - before_fetch(context)                     │   │
         │  │   └─ 构建执行上下文，准备参数                │   │
         │  │ - 自动处理 renew_mode（如果配置）            │   │
         │  │   └─ RenewModeService 计算日期范围           │   │
         │  │ - fetch(context) → List[DataSourceTask]     │   │
         │  │   └─ 生成 Tasks（包含多个 ApiJobs）          │   │
         │  │ - after_fetch(tasks, context)               │   │
         │  │   └─ Tasks 生成后（还未执行）               │   │
         │  └─────────────────────────────────────────────┘   │
         │                                                     │
         │  ┌─────────────────────────────────────────────┐   │
         │  │ Phase 2: 执行阶段                             │   │
         │  │ - before_all_tasks_execute(tasks, context)  │   │
         │  │   └─ 所有 tasks 执行前的统一处理             │   │
         │  │ - TaskExecutor.execute(tasks)                │   │
         │  │   └─ 对每个 task：                            │   │
         │  │       - before_single_task_execute(...)      │   │
         │  │       - 执行 task 的所有 ApiJobs：            │   │
         │  │         ├─ 拓扑排序（根据 depends_on）       │   │
         │  │         ├─ 限流控制（RateLimiter）           │   │
         │  │         ├─ 并发执行（多线程）                │   │
         │  │         └─ 返回结果                          │   │
         │  │       - after_single_task_execute(...)       │   │
         │  │ - after_all_tasks_execute(task_results, ...)│   │
         │  │   └─ 所有 tasks 执行后的统一处理             │   │
         │  └─────────────────────────────────────────────┘   │
         │                                                     │
         │  ┌─────────────────────────────────────────────┐   │
         │  │ Phase 3: 标准化阶段                         │   │
         │  │ - before_normalize(raw_data)               │   │
         │  │   └─ 标准化前                               │   │
         │  │ - normalize(raw_data) → Dict               │   │
         │  │   └─ 字段映射、数据清洗、类型转换            │   │
         │  │ - after_normalize(normalized_data, ...)    │   │
         │  │   └─ 标准化后（保存数据）                   │   │
         │  │ - validate(normalized_data)                │   │
         │  │   └─ Schema 验证                             │   │
         │  └─────────────────────────────────────────────┘   │
         │                                                     │
         └─────────────────────────────────────────────────────┘
```

### TaskExecutor 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│  TaskExecutor.execute(tasks)                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  Step 1: 计算限流值                                 │
         │  - 遍历所有 tasks，收集所有 ApiJobs                 │
         │  - 从 Provider 获取每个 API 的限流声明               │
         │  - 计算每个 task 的最小限流值（木桶效应）            │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  Step 2: 决定线程数                                 │
         │  - 根据 task 数量决定线程数（最多10个）             │
         │  - 根据最小限流值调整线程数                         │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  Step 3: 并行执行 Tasks                             │
         │  使用 MultiThreadWorker 并行执行：                   │
         │                                                     │
         │  for task in tasks:                                 │
         │      ┌─────────────────────────────────────┐        │
         │      │ before_single_task_execute(task)     │        │
         │      └─────────────────────────────────────┘        │
         │      ┌─────────────────────────────────────┐        │
         │      │ 执行 task 的所有 ApiJobs：            │        │
         │      │ 1. 拓扑排序（根据 depends_on）        │        │
         │      │ 2. 按顺序执行：                       │        │
         │      │    for job in sorted_jobs:            │        │
         │      │        - RateLimiter.acquire()        │        │
         │      │        - provider.method(**params)    │        │
         │      │        - 收集结果                      │        │
         │      └─────────────────────────────────────┘        │
         │      ┌─────────────────────────────────────┐        │
         │      │ after_single_task_execute(task_id,   │        │
         │      │                        task_result)  │        │
         │      └─────────────────────────────────────┘        │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  Step 4: 收集结果                                   │
         │  - 返回 {task_id: {job_id: result}} 字典            │
         └────────────────────────────────────────────────────┘
```

### Renew Mode Service 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│  RenewModeService.calculate_date_range()                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │  根据 renew_mode 路由到对应的 Service                │
         └─────────────┬──────────────────────────────────────┘
                       │
         ├─────────────┼─────────────┼─────────────────────────┤
         │             │             │                         │
    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐                    │
    │Incremental│   │ Rolling │   │ Refresh │                  │
    │RenewService│   │RenewService│ │RenewService│              │
    └────┬────┘   └────┬────┘   └────┬────┘                    │
         │             │             │                         │
         │             │             │                         │
    ┌────▼───────────────────────────────────────────────┐  │
    │  Incremental Mode:                                    │  │
    │  - 查询数据库获取最新日期                             │  │
    │  - 从最新日期到 latest_completed_trading_date         │  │
    └──────────────────────────────────────────────────────┘  │
         │                                                     │
    ┌────▼───────────────────────────────────────────────┐  │
    │  Rolling Mode:                                       │  │
    │  - 查询数据库获取最新日期                             │  │
    │  - 计算滚动窗口（最近 N 个时间单位）                  │  │
    │  - 返回 (start_date, end_date)                       │  │
    └──────────────────────────────────────────────────────┘  │
         │                                                     │
    ┌────▼───────────────────────────────────────────────┐  │
    │  Refresh Mode:                                       │  │
    │  - 使用 default_date_range 计算日期范围               │  │
    │  - 如果 default_date_range 为空，使用系统默认         │  │
    │  - 返回 (start_date, end_date)                       │  │
    └──────────────────────────────────────────────────────┘  │
```

---

## 数据流设计

### 完整数据流

```
[Input] 执行上下文（context）
  ├─ latest_completed_trading_date
  ├─ stock_list
  ├─ test_mode, dry_run 等参数
  └─ Handler 自定义参数
  ↓
[Handler] before_fetch(context)
  └─ 构建执行上下文
  ↓
[Handler] fetch(context) → List[DataSourceTask]
  ├─ Task 1: 包含多个 ApiJobs
  ├─ Task 2: 包含多个 ApiJobs
  └─ ...
  ↓
[Handler] after_fetch(tasks, context)
  └─ Tasks 生成后（还未执行）
  ↓
[TaskExecutor] 执行 Tasks
  ├─ 拓扑排序（根据 depends_on）
  ├─ 限流控制（RateLimiter）
  ├─ 并发执行（多线程）
  └─ 返回原始数据：{task_id: {job_id: result}}
  ↓
[Handler] before_normalize(raw_data)
  └─ 标准化前
  ↓
[Handler] normalize(raw_data) → Dict
  ├─ 字段映射（API 字段 → Schema 字段）
  ├─ 数据清洗
  └─ 类型转换
  ↓
[Output] Schema 格式数据
  └─ {"data": [记录1, 记录2, ...]}
  ↓
[Handler] after_normalize(normalized_data)
  └─ 标准化后（保存数据）
  ↓
[DataManager] 保存到数据库
```

### 字段映射流程

**字段映射发生在 Handler 的 `normalize()` 方法中**，这是将第三方 API 的字段名转换为 Schema 字段名的关键步骤。

#### 映射方式

**方式 1: 硬编码映射（代码中直接写）**

```python
# handlers/kline/handler.py
def _map_kline_fields(self, df: pd.DataFrame, stock_id: str) -> pd.DataFrame:
    """映射 K 线字段"""
    mapping = {
        'ts_code': 'id',                    # API 字段 → Schema 字段
        'trade_date': 'date',
        'open': 'open',
        'high': 'highest',
        # ...
    }
    mapped_df = df.rename(columns=mapping)
    return mapped_df
```

**方式 2: 从配置读取**

```python
# handlers/rolling/handler.py
def _apply_field_mapping(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """应用字段映射（从配置中读取）"""
    formatted = []
    for item in records:
        mapped = {}
        # 从 self.field_mapping 读取映射规则
        for target_field, source_field in self.field_mapping.items():
            mapped[target_field] = item.get(source_field)
        formatted.append(mapped)
    return formatted
```

### 映射责任划分

| 组件 | 职责 | 是否负责映射 |
|------|------|------------|
| **Provider** | 调用第三方 API，返回原始数据 | ❌ 不负责映射，只返回 API 原始字段名 |
| **Handler** | 业务逻辑处理，数据标准化 | ✅ **负责映射**，在 `normalize()` 中完成 |
| **Schema** | 定义目标数据结构 | ❌ 不负责映射，只定义目标格式 |
| **DataManager** | 数据持久化 | ❌ 不负责映射，只保存已映射的数据 |

---

## 重要决策记录 (Decisions)

### Decision 1: 职责划分

**日期：** 2025-12-19  
**状态：** 已实施

| 功能 | 定义位置 | 执行位置 | 理由 |
|-----|---------|---------|------|
| **API 限流信息** | Provider（类属性） | TaskExecutor | Provider 只声明元信息 |
| **限流执行** | TaskExecutor | TaskExecutor | 统一管理，线程安全 |
| **多线程调度** | Manager | Manager | 全局视角，运行所有 enabled handler |
| **批量处理** | Handler | Handler | 业务逻辑决定 |
| **数据标准化** | Handler | Handler | 业务逻辑 |
| **依赖处理** | Handler | Handler | Handler 自己解决依赖 |
| **认证配置** | Provider | Provider | 基础设施 |
| **Provider 注入** | mapping.json | Manager | 配置驱动，灵活切换 |
| **全局依赖注入** | Manager | Manager | 统一管理，确保一致性 |

---

### Decision 2: 依赖注入架构

**日期：** 2025-12-19  
**状态：** 已实施

**设计目标：**
1. **统一依赖管理**：在 `renew_data` 开始时统一解析和获取所有需要的全局依赖
2. **按需获取**：只获取真正需要的依赖，避免不必要的开销
3. **配置驱动**：通过 `mapping.json` 显式声明每个 handler 的依赖需求
4. **易于扩展**：预留接口，方便未来添加新的全局依赖
5. **状态隔离**：context 只在 `renew_data` 方法内存在，方法执行完自动销毁

**依赖声明规则：**
1. **显式声明**：每个 handler 必须显式声明所有依赖（即使为 `false`）
2. **布尔值**：`true` 表示需要，`false` 表示不需要
3. **默认值**：如果某个 handler 没有 `dependencies` 字段，默认所有依赖都为 `false`

---

### Decision 3: HandlerConfig 设计

**日期：** 2026-01-17  
**状态：** 已实施

**背景和痛点：**
1. **配置职责混乱**：`mapping.json` 中同时包含 data source 到 handler 的映射配置和 handler 的业务配置
2. **HandlerConfig 类设计困惑**：需要明确哪些配置类应该在 `core` 中，哪些应该在 `userspace` 中
3. **学习成本问题**：需要平衡类型精确性和学习成本

**最终决策：采用方案 A：一个基类（BaseHandlerConfig）**

**理由：**
1. **学习成本最低**：用户只需要知道 `BaseHandlerConfig`
2. **简单直接**：不需要理解复杂的自动选择逻辑、配置冲突检测
3. **灵活性**：所有选项都在一个基类中，用户可以根据需要选择使用
4. **缺点可以接受**：所有 Handler 看到所有选项可以通过文档说明

**设计原则：**
1. **所有选项都在 BaseHandlerConfig 中**：基础选项 + rolling 选项 + simple_api 选项
2. **Config 类是可选的**：如果用户定义了 Config 类，使用 Config 类的默认值；如果没有，直接使用 `mapping.json` 中的字典
3. **两种配置的职责分离**：Handler 默认配置（JSON 文件）和 mapping 配置（覆盖默认值）
4. **配置读取顺序**：JSON 配置文件 → Config 类默认值 → mapping.json → get_param 的 default 参数

---

### Decision 4: Renew Mode 设计

**日期：** 2026-01-XX  
**状态：** 已实施

**设计目标：**
- 统一处理不同数据更新模式（incremental、rolling、refresh）
- 简化 Handler 实现，减少重复代码
- 提供灵活的日期范围计算

**实现方案：**
- 使用 `RenewModeService` 作为统一入口
- 根据 `renew_mode` 路由到对应的 Service（`IncrementalRenewService`、`RollingRenewService`、`RefreshRenewService`）
- Handler 只需配置 `renew_mode` 和相关参数，框架自动处理日期范围计算

**优势：**
- ✅ 代码复用：公共逻辑集中在 Service 中
- ✅ 易于扩展：添加新的 renew mode 只需实现新的 Service
- ✅ 职责清晰：Handler 专注于业务逻辑，日期计算由 Service 负责

---

### Decision 5: 限流设计

**日期：** 2026-01-XX  
**状态：** 已实施

**设计目标：**
- 统一管理 API 限流
- 线程安全
- 防止窗口边界突刺

**实现方案：**
- Provider 声明限流信息（`api_limits` 类属性）
- `TaskExecutor` 负责执行限流（通过 `RateLimiter`）
- 固定窗口限流，窗口对齐到自然分钟
- 窗口切换时强制冷却，防止边界突刺

**优势：**
- ✅ 声明式：Provider 只声明，不执行
- ✅ 统一管理：所有限流逻辑集中在 `TaskExecutor`
- ✅ 线程安全：使用锁和条件变量
- ✅ 防止突刺：窗口切换冷却机制

---

## 版本历史

### 版本 3.0 (2026-01-XX)

**主要变更：**
- 添加运行时 Workflow 详细说明
- 添加重要决策记录 (Decisions) 栏目
- 更新 HandlerConfig 设计决策
- 添加 Renew Mode Service 工作流程
- 添加 TaskExecutor 执行流程

### 版本 2.0 (2025-12-19)

**主要变更：**
- 重构数据源模块架构
- 引入 DataSourceDefinition 标准化配置
- 实现依赖注入架构
- 实现 HandlerConfig 配置系统

### 版本 1.0 (初始版本)

**主要特性：**
- 基础的数据源获取框架
- Provider 和 Handler 分离
- 基本的限流和并发控制

---

## 📚 相关文档

- [README.md](./README.md) - 主要文档，介绍 data source 概念和用法

---

**版本：** 3.0  
**维护者：** @garnet  
**最后更新：** 2026-01-XX
