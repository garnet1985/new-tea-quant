# Data Source 架构设计文档

**版本：** 2.0  
**日期：** 2025-12-19  
**状态：** 生产环境

---

## 📋 目录

1. [设计背景](#设计背景)
2. [核心设计思想](#核心设计思想)
3. [Entity 职责与对应关系](#entity-职责与对应关系)
4. [架构设计](#架构设计)
5. [数据流设计](#数据流设计)
6. [关键设计决策](#关键设计决策)

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
      "params": {}
    }
  }
}
```

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

**不应包含：**
- ❌ 具体的数据获取逻辑
- ❌ 数据标准化逻辑
- ❌ 依赖处理（Handler 自己解决）
- ❌ 限流执行（Handler 自己负责）

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

**不应包含：**
- ❌ 数据获取逻辑
- ❌ 字段映射逻辑
- ❌ 业务逻辑

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

**不应包含：**
- ❌ 多线程调度（由 Manager 负责）
- ❌ 全局限流管理（由 TaskExecutor 负责）

**对应关系：**
- 继承自 `BaseDataSourceHandler`
- 使用一个或多个 `BaseProvider` 实例
- 生成 `DataSourceTask` 列表
- 通过 `DataManager` 保存数据

**生命周期钩子：**
- `before_fetch(context)` - 数据准备阶段，构建执行上下文
- `fetch(context)` - 生成 Tasks（包含多个 ApiJobs）
- `after_fetch(tasks, context)` - Tasks 生成后（还未执行）
- `before_normalize(raw_data)` - 标准化前
- `normalize(raw_data)` - 标准化数据
- `after_normalize(normalized_data)` - 标准化后，通常用于保存数据
- `on_error(error, context)` - 错误处理

---

#### 4. DataSourceTask（业务任务）

**职责：**
- ✅ 封装一个业务任务（包含多个 ApiJobs）
- ✅ 提供任务元信息（task_id, description）

**不应包含：**
- ❌ 执行逻辑（由 TaskExecutor 负责）

**对应关系：**
- 由 `BaseDataSourceHandler.fetch()` 生成
- 包含多个 `ApiJob` 实例
- 被 `TaskExecutor` 执行

**示例：**
```python
task = DataSourceTask(
    task_id="kline_000001.SZ",
    api_jobs=[
        ApiJob(provider_name="tushare", method="get_daily_kline", ...),
        ApiJob(provider_name="tushare", method="get_daily_basic", ...),
    ]
)
```

---

#### 5. ApiJob（API 调用任务）

**职责：**
- ✅ 封装单个 API 调用所需的所有信息
- ✅ 定义依赖关系（`depends_on`）

**不应包含：**
- ❌ 执行逻辑（由 TaskExecutor 负责）

**对应关系：**
- 由 `BaseDataSourceHandler.fetch()` 生成
- 属于某个 `DataSourceTask`
- 被 `TaskExecutor` 执行
- 调用 `BaseProvider` 的方法

**示例：**
```python
job = ApiJob(
    provider_name="tushare",
    method="get_daily_kline",
    params={"ts_code": "000001.SZ", "start_date": "20250101"},
    depends_on=["job_1"],  # 依赖其他 job
    job_id="kline_job_1"
)
```

---

#### 6. TaskExecutor（任务执行器）

**职责：**
- ✅ 执行 `DataSourceTask` 列表
- ✅ 拓扑排序（根据 `depends_on`）
- ✅ 限流控制（通过 `RateLimiter`）
- ✅ 并发管理（多线程执行）
- ✅ 错误处理和重试

**不应包含：**
- ❌ 数据标准化逻辑
- ❌ 业务逻辑

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

**不应包含：**
- ❌ 业务逻辑
- ❌ 数据标准化
- ❌ 限流执行逻辑
- ❌ 多线程调度

**对应关系：**
- 被 `BaseDataSourceHandler` 使用
- 被 `TaskExecutor` 调用
- 通过 `ProviderInstancePool` 管理实例

---

#### 8. ProviderInstancePool（Provider 实例池）

**职责：**
- ✅ 管理 Provider 实例（懒加载）
- ✅ 多进程安全（使用文件锁）
- ✅ 实例复用

**对应关系：**
- 管理多个 `BaseProvider` 实例
- 被 `TaskExecutor` 使用

---

#### 9. RateLimiter（限流器）

**职责：**
- ✅ 固定窗口限流
- ✅ 线程安全
- ✅ 窗口边界处理

**对应关系：**
- 被 `TaskExecutor` 使用
- 每个 `(provider, api_name)` 一个实例

---

#### 10. DataManager（数据管理器）

**职责：**
- ✅ 提供数据库访问服务
- ✅ 提供业务服务（stock, macro 等）

**对应关系：**
- 被 `BaseDataSourceHandler` 使用（保存数据）
- 被 `DataSourceManager` 使用（读取依赖数据）

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

**配置**（mapping.json）：
```json
{
  "gdp": {
    "params": {
      "field_mapping": {
        "quarter": "quarter",
        "gdp": "gdp",
        "gdp_yoy": "gdp_yoy"
      }
    }
  }
}
```

### 映射流程图

```
Provider 返回原始数据
  ↓
DataFrame/原始数据
  ├── 字段名：ts_code, trade_date, open, high, low, ...
  └── 字段值：000001.SZ, 20240101, 10.5, 11.0, 10.0, ...
  ↓
Handler.normalize()  ← ⭐ 字段映射发生在这里
  ├── 读取映射规则（硬编码或配置）
  ├── 执行字段映射
  │   ├── ts_code → id
  │   ├── trade_date → date
  │   ├── high → highest
  │   └── ...
  └── 类型转换（如 str → float）
  ↓
Schema 格式数据
  ├── 字段名：id, date, open, highest, lowest, ...
  └── 字段值：000001.SZ, 20240101, 10.5, 11.0, 10.0, ...
  ↓
Schema.validate() 验证
  ↓
DataManager 保存到数据库
```

### 映射责任划分

| 组件 | 职责 | 是否负责映射 |
|------|------|------------|
| **Provider** | 调用第三方 API，返回原始数据 | ❌ 不负责映射，只返回 API 原始字段名 |
| **Handler** | 业务逻辑处理，数据标准化 | ✅ **负责映射**，在 `normalize()` 中完成 |
| **Schema** | 定义目标数据结构 | ❌ 不负责映射，只定义目标格式 |
| **DataManager** | 数据持久化 | ❌ 不负责映射，只保存已映射的数据 |

### 为什么在 Handler 中映射？

1. **业务逻辑集中**：每个数据源的映射规则不同，Handler 最了解自己的业务逻辑
2. **灵活性**：可以处理复杂的映射（如字段计算、条件映射）
3. **可配置性**：可以通过配置或代码灵活定义映射规则

---

## 关键设计决策

### 职责划分

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

### 依赖注入架构

**设计目标：**
1. **统一依赖管理**：在 `renew_data` 开始时统一解析和获取所有需要的全局依赖
2. **按需获取**：只获取真正需要的依赖，避免不必要的开销
3. **配置驱动**：通过 `mapping.json` 显式声明每个 handler 的依赖需求
4. **易于扩展**：预留接口，方便未来添加新的全局依赖
5. **状态隔离**：context 只在 `renew_data` 方法内存在，方法执行完自动销毁

**架构层次：**
```
renew_data()
  ↓
[Step 1] Dependency Resolution（依赖解析层）
  - 读取 mapping.json，找出所有 is_enabled=true 的 handler
  - 收集每个 handler 声明的依赖需求（dependencies）
  - 去重，得到需要获取的全局依赖列表
  ↓
[Step 2] Dependency Injection（依赖注入层）
  - 根据依赖列表，获取所有需要的全局依赖
  - 构建 shared_context（包含 latest_completed_trading_date, stock_list 等）
  - 添加执行参数（test_mode, dry_run 等）
  ↓
[Step 3] Build Context Layer（构建上下文层）
  - 遍历所有启用的 handler
  - 调用每个 handler 的 before_fetch(context=shared_context)
  - handler 可以读取 shared_context 中的全局依赖，并添加自己的特定 context
  ↓
[Step 4] Handler Execution Layer（处理器执行层）
  - fetch, normalize, after_normalize 等
```

**依赖声明规则：**
1. **显式声明**：每个 handler 必须显式声明所有依赖（即使为 `false`）
2. **布尔值**：`true` 表示需要，`false` 表示不需要
3. **默认值**：如果某个 handler 没有 `dependencies` 字段，默认所有依赖都为 `false`

---

## HandlerConfig 设计决策

**日期：** 2026-01-17  
**状态：** 已实施

---

### 背景和痛点

在重构 Handler 配置系统时，我们面临以下问题：

1. **配置职责混乱**：
   - `mapping.json` 中同时包含 data source 到 handler 的映射配置和 handler 的业务配置
   - Handler 的默认配置和针对特定 data source 的配置混在一起
   - 难以区分哪些是 Handler 的"出厂设置"，哪些是针对特定 data source 的"个性化设置"

2. **HandlerConfig 类设计困惑**：
   - 最初在 `core` 模块中定义了多个业务特定的 `HandlerConfig` 类（如 `KlineHandlerConfig`）
   - 但根据"所有 handlers 都是用户自定义"的原则，这些配置类不应该在框架中定义
   - 需要明确：哪些配置类应该在 `core` 中，哪些应该在 `userspace` 中

3. **学习成本问题**：
   - 如果采用多个基类（如 `RollingHandlerConfig`、`SimpleApiHandlerConfig`），用户需要知道（已废弃，现在使用单一基类）：
     - 有哪些基类可用
     - 自己的 Handler 应该继承哪个基类
     - 系统如何自动选择基类
     - 配置冲突如何检测和处理
   - 如果采用一个基类（`BaseHandlerConfig`），虽然学习成本低，但所有 Handler 会看到所有选项

---

### 讨论的方案

#### 方案 A：一个基类（BaseHandlerConfig）

**设计**：
- 只有一个 `BaseHandlerConfig` 基类
- 包含所有选项（基础选项 + rolling 选项 + simple_api 选项）
- 用户只需要继承 `BaseHandlerConfig`，定义业务相关字段

**优点**：
- ✅ 学习成本最低：用户只需要知道 `BaseHandlerConfig`
- ✅ 简单直接：不需要理解复杂的自动选择逻辑
- ✅ 灵活性：所有选项都在一个基类中，用户可以选择使用

**缺点**：
- ❌ 所有 Handler 看到所有选项（但可以通过文档说明）
- ❌ IDE 自动补全显示所有选项（用户可以选择忽略）
- ❌ 类型不够精确（但可以通过命名约定和文档弥补）

#### 方案 B：多个基类（自动选择）

**设计**：
- 多个基类：`BaseHandlerConfig`、`RollingHandlerConfig`、`SimpleApiHandlerConfig`（已废弃，现在使用单一基类）
- 系统根据 Handler 类名自动判断类型，选择对应的 Config 类
- 如果配置冲突（如同时包含 rolling 和 incremental 选项），报错拒绝执行

**优点**：
- ✅ 类型更精确：每个 Handler 只看到相关选项
- ✅ IDE 自动补全更准确

**缺点**：
- ❌ 学习成本中等：用户需要知道有多个基类（虽然系统自动选择）
- ❌ 如果配置冲突，需要理解为什么报错
- ❌ 如果用户想定义自己的 Config 类，需要知道该继承哪个

#### 方案 C：显式声明类型

**设计**：
- 在 `mapping.json` 中显式声明 `handler_type`（如 `"rolling"`、`"simple_api"`）
- 系统根据 `handler_type` 选择对应的 Config 类

**优点**：
- ✅ 明确清晰：用户显式声明类型

**缺点**：
- ❌ 学习成本较高：用户需要知道 `handler_type` 字段、有哪些类型可选
- ❌ 增加配置复杂度

---

### 最终决策

**采用方案 A：一个基类（BaseHandlerConfig）**

**理由**：
1. **学习成本最低**：用户只需要知道 `BaseHandlerConfig`
2. **简单直接**：不需要理解复杂的自动选择逻辑、配置冲突检测
3. **灵活性**：所有选项都在一个基类中，用户可以根据需要选择使用
4. **缺点可以接受**：
   - 所有 Handler 看到所有选项 → 可以通过文档说明哪些选项适用于哪些 Handler
   - IDE 自动补全显示所有选项 → 用户可以选择忽略不相关的
   - 类型不够精确 → 可以通过命名约定和文档弥补

---

### 设计原则

1. **所有选项都在 BaseHandlerConfig 中**：
   - 基础选项：所有 Handler 都可以使用
   - rolling 相关选项：适用于需要滚动刷新的业务 Handler（如 `GdpHandler`、`ShiborHandler`、`LprHandler`）
     - `rolling_periods`: 滚动刷新周期数（根据 date_format 自动识别单位）
     - `rolling_months`: 滚动刷新月数（如 PriceIndexesHandler）
     - `date_format`: 日期格式（quarter | month | date | none）
   - 用户可以根据需要选择使用相关选项

2. **Config 类是可选的**：
   - 如果用户定义了 Config 类：使用 Config 类的默认值，`mapping.json` 覆盖，提供类型安全
   - 如果用户没有定义 Config 类：直接使用 `mapping.json` 中的字典，通过 `get_param` 读取

3. **两种配置的职责分离**：
   - **Handler 独有的配置**（Handler 内部定义）：
     - 定义 Handler 的默认行为
     - 位置：Handler 的 Config 类中（可选）
     - 作用：Handler 的"出厂设置"
   - **mapping.json 中的配置**（连接 data source 和 handler）：
     - 选择使用哪个 handler
     - 覆盖或补充 Handler 的默认配置
     - 位置：`mapping.json`
     - 作用：针对特定 data source 的"个性化设置"

4. **配置读取顺序**：
   - Handler 的 Config 类默认值（如果定义了 Config 类）
   - `mapping.json` 中的 `handler_config`（覆盖默认值）
   - `get_param` 的 `default` 参数（最终后备）

---

### 实现细节

#### BaseHandlerConfig 结构

```python
@dataclass
class BaseHandlerConfig:
    """
    Handler 配置基类
    
    包含所有 Handler 配置选项（基础 + rolling + simple_api）。
    学习成本最低：用户只需要继承此类，定义自己业务相关的字段即可。
    """
    # ========== Rolling/SimpleApi 通用选项 ==========
    provider_name: str = "tushare"
    method: str = ""
    date_format: str = "date"
    default_date_range: Dict[str, int] = field(default_factory=dict)
    rolling_periods: Optional[int] = None
    rolling_months: Optional[int] = None
    table_name: Optional[str] = None
    date_field: Optional[str] = None
    requires_date_range: bool = True
    custom_before_fetch: Optional[Callable] = None
    custom_normalize: Optional[Callable] = None
```

#### 用户定义 Config 类示例

```python
# userspace/data_source/handlers/kline/config.py
from core.modules.data_source.data_classes.handler_config import BaseHandlerConfig
from dataclasses import dataclass
from typing import Optional

@dataclass
class KlineHandlerConfig(BaseHandlerConfig):
    # 只需要定义业务相关的字段
    debug_limit_stocks: Optional[int] = None
    # 其他选项（如 rolling_periods）也在 BaseHandlerConfig 中，可以根据需要使用
```

#### 配置发现机制

1. **Handler 定义 `config_class` 属性**：
   ```python
   class KlineHandler(BaseDataSourceHandler):
       config_class = KlineHandlerConfig
   ```

2. **系统自动发现**：
   - `DataSourceDefinition._parse_handler_config()` 首先检查 Handler 类是否定义了 `config_class` 属性
   - 如果定义了，使用该 Config 类
   - 如果没有定义，返回 `None`，直接使用 `mapping.json` 中的字典

3. **配置合并**：
   - 如果定义了 Config 类，使用 Config 类的默认值
   - `mapping.json` 中的 `handler_config` 覆盖默认值
   - 通过 `get_param()` 读取，支持 fallback 机制

---

### 配置分离实现（已完成）

**实现日期：** 2026-01-17

**设计目标：**
- 将 Handler 的默认配置从 `mapping.json` 中分离出来
- `mapping.json` 只负责 data source 到 handler 的映射和覆盖配置
- Handler 的默认配置存储在 JSON 文件中，通过 Config 数据类提供类型安全

**实现方案：**

1. **JSON 配置文件位置**：
   - `userspace/data_source/handlers/{handler_name}/config.json`
   - 存储 Handler 的默认配置（"出厂设置"）

2. **配置读取顺序**：
   ```
   JSON 配置文件（默认值）
     ↓
   Config 数据类（类型安全）
     ↓
   mapping.json 中的 handler_config（覆盖）
     ↓
   get_param 的 default 参数（最终后备）
   ```

3. **实现细节**：
   - `_extract_handler_name()`: 从 handler_path 提取 handler_name
   - `_load_handler_config_json()`: 从 JSON 文件加载配置
   - `_parse_handler_config()`: 实现完整的配置读取和合并逻辑

4. **配置合并逻辑**：
   ```python
   # Step 1: 从 JSON 文件读取默认配置
   json_config = cls._load_handler_config_json(handler_name)
   
   # Step 2: 检查 Handler 类是否定义了 config_class
   config_class = handler_class.config_class
   
   # Step 3: 合并配置（JSON 配置 → mapping.json 配置）
   merged_config = {**json_config, **mapping_config}
   
   # Step 4: 创建 Config 实例
   return config_class(**merged_config)
   ```

**优势：**
- ✅ 配置分离：Handler 默认配置和 mapping 配置职责清晰
- ✅ 类型安全：通过 Config 数据类提供类型检查和 IDE 支持
- ✅ 灵活性：用户可以选择使用 JSON 配置或直接使用 mapping.json
- ✅ 向后兼容：如果 JSON 文件不存在，使用 Config 类的默认值

---

### 后续工作

1. **文档完善**：
   - 在 `BaseHandlerConfig` 的文档中说明哪些选项适用于哪些 Handler
   - 提供使用示例和最佳实践

---

## 📚 相关文档

- [README.md](./README.md) - 主要文档，介绍 data source 概念和用法

---

**版本：** 2.0  
**维护者：** @garnet  
**最后更新：** 2026-01-17
