# Data Source 模块

## 📋 概述

Data Source 模块是一个灵活、简单、强大的数据获取框架，用于统一管理从多个第三方数据源（如 Tushare、AKShare、EastMoney）获取数据的过程。

### 核心特性

- ✅ **简单直观**：核心概念清晰，易于理解
- ✅ **极致灵活**：用户完全控制数据获取逻辑
- ✅ **多实现共存**：一个 data source 可以有多个 handler 实现（不同实现方式），但**运行时只能选择一个 handler**，不能同时运行多个 handler（避免数据互相覆盖）
- ✅ **运行时切换**：通过配置文件切换 handler，无需修改代码
- ✅ **易于扩展**：添加新 data source 或 handler 不影响现有代码
- ✅ **配置驱动**：通过 `mapping.py`（DATA_SOURCES）配置 handler 的启用、依赖和参数

---

## 🎯 什么是 Data Source？

**Data Source（数据源）** 是框架中的一个核心概念，代表**框架需要的一种数据类型**。

### 从 Input 和 Output 角度理解

一个 Data Source 可以理解为：

**我要产生一种数据（Schema 的定义帮助我定义出我需要的这种数据的标准格式），那么：**

#### 1. 简单场景：单个 API

从数据输入的角度来理解，我需要**至少一个 Provider 的某一个 API** 给我提供数据，然后我再把数据按照 Schema 的标准化进行筛选。即从 Provider 的 API 返回值里提取一些（或全部）的字段，重命名成 Schema 的字段名，这样我就得到了我想要的数据结构。

**示例：**
- Schema 定义：`{"id": DataSourceField(...), "name": DataSourceField(...), "price": DataSourceField(...)}`
- Provider API 返回：`{"ts_code": "000001.SZ", "name": "平安银行", "close": 10.5}`
- 字段映射：`ts_code → id`, `close → price`（`name` 保持不变）
- 最终输出：`{"id": "000001.SZ", "name": "平安银行", "price": 10.5}`

#### 2. 复杂场景：多个 API 协作

然而，上边只是最简单的例子。在有些情况下，我们想要的数据可能需要**多个 API 一起协作完成**，这些 API 甚至可能不是来源于同一个 Provider。更甚至，这些 API 之间产生了**依赖关系**：某个 API 可能并不直接对我们的结果产生输入贡献，而是作为另一个真正产生输入贡献的 API 的依赖。

**示例：**
- 需要获取 5 个字段：`id`, `date`, `open`, `close`, `volume`
- API 1（贡献字段）：获取 K 线数据 → 贡献 `id`, `date`, `open`, `close`
- API 2（贡献字段）：获取成交量数据 → 贡献 `volume`
- API 3（依赖 API）：获取股票列表 → 作为 API 1 的依赖（用于确定要获取哪些股票）

在这种情况下，我们的 Data Source 配置会略微复杂，需要配置 API 之间的 `depends_on` 关系来解决依赖问题。这种情况也解释了**为什么不是所有 API 都对最终输出有直接的数据贡献**。

#### 3. 框架自动处理

Data Source 的产出结果可能是 **N 个来源于不同 Provider 的 N 个 API 结果拼接** 来的。框架会根据配置自动解析 API 的依赖关系和贡献关系，完成数据源的获取：

- **依赖解析**：框架会根据 `depends_on` 配置进行拓扑排序，确保依赖的 API 先执行
- **字段映射**：框架会根据每个 API 的 `field_mapping` 配置，将 API 字段映射到 Schema 字段
- **数据合并**：Handler 的 `normalize()` 方法负责将多个 API 的结果合并成最终的 Schema 格式数据

```
┌─────────────────────────────────────────────────┐
│              Data Source                         │
│                                                  │
│  Input（输入）:                                   │
│  - 执行上下文（context）                          │
│    ├─ latest_completed_trading_date              │
│    ├─ stock_list                                 │
│    ├─ test_mode, dry_run 等参数                   │
│    └─ Handler 自定义参数                          │
│                                                  │
│  Processing（处理）:                              │
│  - Handler 生成 Tasks（包含多个 API 调用）       │
│  - TaskExecutor 执行 Tasks                       │
│  - Handler 标准化数据                            │
│                                                  │
│  Output（输出）:                                  │
│  - 符合 Schema 格式的数据                        │
│    └─ {"data": [记录1, 记录2, ...]}              │
│                                                  │
└─────────────────────────────────────────────────┘
```

> 💡 **提示**：详细的运行时 Workflow 和完整数据流请参考 [架构文档](../../../docs/architecture/core_modules/data_source/architecture.md)。

### 示例：K 线数据源

**Input（输入）**：
```python
context = {
    "latest_completed_trading_date": "20251222",
    "stock_list": ["000001.SZ", "000002.SZ", ...],
    "test_mode": False,
    "dry_run": False
}
```

**Processing（处理）**：
1. `KlineHandler` 生成 Tasks：
   - Task 1: 获取 000001.SZ 的日线、周线、月线数据（3 个 ApiJobs）
   - Task 2: 获取 000002.SZ 的日线、周线、月线数据（3 个 ApiJobs）
   - ...

2. `TaskExecutor` 执行 Tasks：
   - 调用 Tushare API 获取 K 线数据
   - 调用 Tushare API 获取 daily_basic 数据
   - 合并数据

**Output（输出）**：
```python
{
    "data": [
        {
            "id": "000001.SZ",
            "term": "daily",
            "date": "20251222",
            "open": 10.5,
            "highest": 11.0,
            "lowest": 10.0,
            "close": 10.8,
            "volume": 1000000,
            "amount": 11000000,
            # ... 其他字段
        },
        # ... 更多记录
    ]
}
```

---

### 核心概念详解

为了更好地理解 Data Source，我们需要了解几个核心概念：

#### 什么是 Schema（数据格式规范）？

**Schema 就是数据的"模板"**，它定义了：
- 这个 Data Source 需要哪些字段？
- 每个字段是什么类型？（字符串、数字、日期等）
- 哪些字段是必需的？哪些是可选的？

**打个比方**：Schema 就像是一张表格的表头，告诉你每一列应该叫什么名字、应该填什么类型的数据。

**示例：**
```python
from core.modules.data_source.data_class.field import DataSourceField
from core.modules.data_source.data_class.schema import DataSourceSchema

KLINE = DataSourceSchema(
    name="kline",
    fields={
        "id": DataSourceField(str, required=True),      # 股票代码，字符串，必需
        "date": DataSourceField(str, required=True),     # 交易日期，字符串，必需
        "open": DataSourceField(float, required=True),   # 开盘价，数字，必需
        "close": DataSourceField(float, required=True), # 收盘价，数字，必需
        "volume": DataSourceField(int, required=False), # 成交量，整数，可选
    }
)
```

**作用**：
- 告诉 Handler："你最终输出的数据必须符合这个格式"
- 告诉框架："验证一下数据是否符合规范"
- 告诉数据库："按照这个结构建表"

---

#### 什么是 Provider（数据提供方）？

**Provider 就是第三方数据源的"封装器"**，它负责：
- 调用第三方 API（如 Tushare、AKShare、EastMoney）
- 处理认证（token、api_key 等）
- 声明限流信息（这个 API 每分钟能调用多少次）
- 统一错误格式

**打个比方**：Provider 就像是一个"翻译官"，把第三方 API 的调用方式统一成框架能理解的格式。

**Provider 里有什么？**

1. **API 方法**：封装第三方 API 的调用
   ```python
   class TushareProvider(BaseProvider):
       def get_daily_kline(self, ts_code, start_date, end_date):
           # 调用 Tushare 的 API
           return self.pro.daily(**params)
   ```

2. **认证信息**：告诉框架这个 Provider 需要什么认证
   ```python
   provider_name = "tushare"
   requires_auth = True
   auth_type = "token"  # 需要 token 认证
   ```

3. **限流声明**：告诉框架每个 API 的限流规则（框架会自动执行限流）
   ```python
   api_limits = {
       "get_daily_kline": 200,  # 每分钟最多 200 次
       "get_stock_list": 800,   # 每分钟最多 800 次
   }
   ```

**特点**：
- ✅ **纯 API 封装**：不包含业务逻辑，只负责调用 API
- ✅ **声明式**：只声明限流、认证等信息，不执行限流逻辑
- ✅ **简单可测试**：每个方法只做一件事

---

#### 什么是 Handler（获取方法定义）？

**Handler 就是"如何获取数据"的实现**，它负责：
- 决定调用哪些 Provider 的哪些 API
- 处理多个 API 之间的依赖关系
- 将原始数据转换成符合 Schema 的格式
- 保存数据到数据库

**打个比方**：Handler 就像是一个"厨师"，知道：
- 需要哪些"食材"（调用哪些 API）
- 这些"食材"的先后顺序（依赖关系）
- 如何"烹饪"（数据转换和合并）
- 最终"装盘"（保存到数据库）

**Handler 里有什么？**

1. **fetch() 方法**：生成任务列表
   ```python
   async def fetch(self, context):
       # 根据 context（如股票列表）生成多个 Tasks
       tasks = []
       for stock in context["stock_list"]:
           task = DataSourceTask(
               task_id=f"kline_{stock}",
               api_jobs=[
                   ApiJob(provider_name="tushare", method="get_daily_kline", ...),
                   ApiJob(provider_name="tushare", method="get_daily_basic", ...),
               ]
           )
           tasks.append(task)
       return tasks
   ```

2. **normalize() 方法**：标准化数据
   ```python
   async def normalize(self, raw_data):
       # raw_data: {task_id: {job_id: result}}
       # 将多个 API 的结果合并，字段映射，数据清洗
       formatted = []
       for task_id, task_result in raw_data.items():
           # 合并 K 线数据和 daily_basic 数据
           # 字段映射：ts_code → id, trade_date → date
           # 类型转换、数据清洗
           formatted.append(mapped_record)
       return {"data": formatted}
   ```

3. **生命周期钩子**：在数据获取的不同阶段执行自定义逻辑
   - `before_fetch()`: 数据准备阶段
   - `after_fetch()`: Tasks 生成后
   - `before_normalize()`: 标准化前
   - `after_normalize()`: 标准化后（通常用于保存数据）

**特点**：
- ✅ **业务逻辑集中**：所有数据获取和转换的逻辑都在这里
- ✅ **完全可控**：用户完全控制如何获取数据
- ✅ **灵活扩展**：可以处理复杂的多 API 协作场景

---

#### SimpleConfigHandler - 纯配置驱动的 Handler

**SimpleConfigHandler 是一个通用的 Handler，可以通过配置完成简单的数据获取任务，无需编写代码。**

**适用场景：**
- ✅ 简单的 API 调用（单次调用，无复杂逻辑）
- ✅ 需要字段映射
- ✅ 可选：滚动刷新
- ✅ 可选：自动保存到数据库

**使用方式：**

在 `mapping.json` 中配置，无需编写任何代码：

```json
{
  "data_sources": {
    "my_simple_data": {
      "handler": "core.modules.data_source.simple_config_handler.SimpleConfigHandler",
      "is_enabled": true,
      "provider_config": {
        "apis": [
          {
            "provider_name": "tushare",
            "method": "get_stock_list",
            "field_mapping": {
              "code": "ts_code",
              "name": "name"
            }
          }
        ]
      },
      "handler_config": {
        "table_name": "stock_list",
        "requires_date_range": false
      }
    }
  }
}
```

**如果需要滚动刷新：**

```json
{
  "data_sources": {
    "gdp": {
      "handler": "core.modules.data_source.simple_config_handler.SimpleConfigHandler",
      "is_enabled": true,
      "provider_config": {
        "apis": [
          {
            "provider_name": "tushare",
            "method": "get_gdp",
            "field_mapping": {
              "quarter": "quarter",
              "gdp": "gdp"
            }
          }
        ]
      },
      "handler_config": {
        "date_format": "quarter",
        "rolling_periods": 4,
        "default_date_range": {"years": 5},
        "table_name": "gdp",
        "date_field": "quarter",
        "requires_date_range": true
      }
    }
  }
}
```

**配置说明：**
- `provider_name`: Provider 名称（如 "tushare"）
- `method`: API 方法名
- `field_mapping`: 字段映射（API 字段 → Schema 字段）
- `table_name`: 数据库表名（如果配置，会自动保存数据）
- `date_field`: 日期字段名（用于滚动刷新和数据保存）
- `date_format`: 日期格式（"quarter" | "month" | "date" | "none"）
- `rolling_periods`: 滚动刷新周期数（如果配置，会自动启用滚动刷新）
- `default_date_range`: 默认日期范围（如 `{"years": 5}`）
- `requires_date_range`: 是否需要日期范围参数

**优势：**
- ✅ **零代码**：完全通过配置完成，无需编写 Handler 代码
- ✅ **快速上手**：适合简单的数据源，快速配置即可使用
- ✅ **自动功能**：自动支持滚动刷新、字段映射、数据保存

**限制：**
- ❌ 只支持单 API 调用（不支持多 API 协作）
- ❌ 不支持复杂的业务逻辑（如需复杂逻辑，请使用自定义 Handler）

---

#### 什么是 ApiJob（API 调用任务）？

**ApiJob 就是"一次 API 调用"的封装**，它包含：
- 调用哪个 Provider 的哪个方法
- 调用时传入什么参数
- 依赖哪些其他的 ApiJob（必须先执行）

**打个比方**：ApiJob 就像是一张"采购清单"，告诉框架：
- 去哪里买（哪个 Provider）
- 买什么（哪个 API 方法）
- 买多少（参数）
- 需要先买什么（依赖关系）

**示例：**
```python
ApiJob(
    provider_name="tushare",           # 使用 Tushare Provider
    method="get_daily_kline",          # 调用 get_daily_kline 方法
    params={                           # 调用参数
        "ts_code": "000001.SZ",
        "start_date": "20250101",
        "end_date": "20250131"
    },
    depends_on=["get_stock_list"],     # 依赖：先执行 get_stock_list
    job_id="kline_000001"              # Job ID（用于依赖关系）
)
```

---

#### 什么是 DataSourceTask（业务任务）？

**DataSourceTask 就是"一个完整的业务任务"**，它包含：
- 多个 ApiJob（可能需要多个 API 协作）
- 任务 ID 和描述

**打个比方**：DataSourceTask 就像是一个"完整的采购计划"，包含多个"采购清单"（ApiJob）。

**示例：**
```python
DataSourceTask(
    task_id="kline_000001.SZ",         # 任务 ID
    api_jobs=[                          # 包含多个 API 调用
        ApiJob(provider_name="tushare", method="get_daily_kline", ...),
        ApiJob(provider_name="tushare", method="get_daily_basic", ...),
    ],
    description="获取 000001.SZ 的 K 线数据"
)
```

**为什么需要 Task？**
- 一个业务任务可能需要多个 API 协作（如获取 K 线需要调用 2 个 API）
- 一个 Data Source 可能需要处理多个业务任务（如获取多个股票的 K 线）
- Task 让代码更清晰：一个 Task = 一个完整的业务逻辑

---

#### 什么是 TaskExecutor（任务执行器）？

**TaskExecutor 就是"执行任务的引擎"**，它负责：
- 解析 Task 和 ApiJob 的依赖关系
- 进行拓扑排序（确保依赖的 API 先执行）
- 限流控制（根据 Provider 声明的限流规则）
- 并发执行（多线程执行，提高效率）
- 错误处理和重试

**打个比方**：TaskExecutor 就像是一个"智能调度系统"，知道：
- 哪些任务必须先做（依赖关系）
- 什么时候能做（限流控制）
- 如何高效地做（并发执行）

**工作流程：**
```
1. 接收 Handler 生成的 Tasks 列表
2. 解析所有 ApiJob 的依赖关系（depends_on）
3. 拓扑排序：确定执行顺序
4. 限流控制：根据 Provider 的 api_limits 声明，控制调用频率
5. 并发执行：多线程执行，提高效率
6. 返回结果：{task_id: {job_id: result}}
```

---

#### 什么是 DataSourceManager（数据源管理器）？

**DataSourceManager 就是"总指挥"**，它负责：
- 加载所有 Schema 定义
- 加载 Handler 配置（mapping.json）
- 管理全局依赖（如 `latest_completed_trading_date`、`stock_list`）
- 执行所有启用的 Handler

**打个比方**：DataSourceManager 就像是一个"项目经理"，负责：
- 了解所有可用的"资源"（Schema、Handler）
- 协调"全局资源"（全局依赖）
- 执行"项目计划"（运行所有启用的 Handler）

**主要方法：**
- `renew_data()`: 执行所有启用的 Handler，更新数据
- `fetch(data_source_name, context)`: 测试单个 Handler
- `list_data_sources()`: 列出所有可用的 Data Source

---

## 🏗️ 快速参考

### 层次关系

```
Data Source (框架需要的数据类型)
    ↓ 对应唯一
Schema (数据格式规范)
    ↓ 可以有多个实现（但运行时只选一个）
Handler (获取方法定义)
    ↓ 可能使用多个
Provider (第三方数据源)
```

### 核心概念速查

| 概念 | 作用 | 关键点 |
|------|------|--------|
| **Data Source** | 框架需要的一种数据类型 | 业务导向，与技术实现无关 |
| **Schema** | 数据格式规范 | 定义字段、类型，验证数据 |
| **Handler** | 获取数据的方法实现 | 业务逻辑集中，完全可控 |
| **Provider** | 第三方数据源封装 | 纯 API 封装，声明式元数据 |
| **ApiJob** | 单个 API 调用任务 | 包含 Provider、方法、参数、依赖 |
| **DataSourceTask** | 业务任务 | 包含多个 ApiJob |
| **TaskExecutor** | 任务执行引擎 | 依赖解析、限流、并发执行 |
| **DataSourceManager** | 总指挥 | 加载配置、管理依赖、执行 Handler |

> 💡 **提示**：详细的解释请参考上面的"核心概念详解"章节。

---

## 🏗️ 架构组件

### DataSourceManager（数据源管理器）

**职责：**
- 加载 Schema 定义
- 加载 Handler 映射配置并动态加载 handler
- 执行数据获取（`renew_data` 方法）
- 管理全局依赖注入（`latest_completed_trading_date`、`stock_list` 等）

**使用示例：**
```python
from core.modules.data_source.data_source_manager import DataSourceManager

# 初始化
manager = DataSourceManager(is_verbose=False)

# 执行数据更新（配置驱动，自动运行所有启用的 handler）
await manager.renew_data(
    latest_completed_trading_date="20251222",
    stock_list=None,  # 如果不提供，会自动从数据库读取
    test_mode=False,
    dry_run=False
)
```

### BaseDataSourceHandler（Handler 基类）

**职责：**
- 定义 Handler 生命周期钩子
- 提供模板方法 `execute()` 执行完整流程
- 管理 Provider 实例

**生命周期钩子：**
- `before_fetch(context)` - 数据准备阶段，构建执行上下文
- `fetch(context)` - 生成 Tasks（包含多个 ApiJobs）
- `after_fetch(tasks, context)` - Tasks 生成后（还未执行）
- `before_normalize(raw_data)` - 标准化前
- `normalize(raw_data)` - 标准化数据
- `after_normalize(normalized_data)` - 标准化后，通常用于保存数据
- `on_error(error, context)` - 错误处理

**执行流程：**
```
execute(context)
  ↓
before_fetch(context)  # 构建上下文
  ↓
fetch(context) → List[DataSourceTask]  # 生成 Tasks
  ↓
after_fetch(tasks, context)  # Tasks 生成后
  ↓
框架执行 Tasks（TaskExecutor）
  ↓
before_normalize(raw_data)  # 标准化前
  ↓
normalize(raw_data) → Dict  # 标准化数据
  ↓
after_normalize(normalized_data)  # 标准化后（保存数据）
```

### BaseProvider（Provider 基类）

**职责：**
- 封装第三方 API 调用
- 声明 API 限流信息（不执行）
- 认证配置和验证
- 错误转换（统一错误格式）

**特点：**
- 纯 API 封装，不包含业务逻辑
- 声明式元数据（限流、认证信息作为类属性）
- 简单可测试

---

## 📂 目录结构

```
core/modules/data_source/
├── README.md                       # 主要文档（本文档）
├── __init__.py
├── data_source_manager.py          # 数据源管理器
├── renew_manager.py                # Renew 编排层
├── execution_scheduler.py          # 执行调度器
├── base_class/                     # 基类
│   ├── base_handler.py            # Handler 基类
│   └── base_provider.py           # Provider 基类
├── data_class/                     # 数据类定义
│   ├── schema.py                  # Schema 定义
│   ├── field.py                   # Field 定义
│   ├── api_job.py                 # ApiJob 定义
│   ├── api_job_batch.py           # ApiJobBatch 定义
│   ├── config.py                  # Config 定义
│   └── error.py                   # Error 定义
├── service/                        # 服务层
│   ├── handler_helper.py          # Handler 辅助方法
│   ├── manager_helper.py          # Manager 辅助方法
│   ├── provider_helper.py          # Provider 辅助方法
│   ├── api_job_executor.py        # API Job 执行器
│   ├── rate_limiter.py            # 限流器
│   └── renew/                      # Renew 服务
│       ├── renew_common_helper.py # Renew 公共工具
│       ├── incremental_renew_service.py  # 增量更新服务
│       ├── rolling_renew_service.py     # 滚动刷新服务
│       └── refresh_renew_service.py     # 全量刷新服务
└── examples/                       # 示例代码
    └── extreme_renew_scenarios.py

userspace/data_source/
├── mapping.py                      # 用户配置（必需，定义 DATA_SOURCES）
├── providers/                      # 用户自定义 Provider
│   ├── tushare/
│   ├── akshare/
│   └── eastmoney/
└── handlers/                       # 用户自定义 Handler
    ├── kline/
    ├── corporate_finance/
    └── stock_list/
```

---

## 📄 配置文件

### 配置文件分离设计

Handler 配置采用**分离设计**，降低学习成本：

1. **Handler 默认配置** → `handlers/{handler_name}/config.json`（JSON 文件）
2. **mapping.json 配置** → 只用于覆盖默认配置（可选）

**配置读取顺序：**
1. 从 JSON 文件读取默认配置（`handlers/{handler_name}/config.json`）
2. 检查 Handler 类是否定义了 `config_class` 属性
3. 如果定义了 `config_class`，创建 Config 实例（JSON 配置作为默认值）
4. `mapping.json` 中的 `handler_config` 覆盖 JSON 配置和 Config 类默认值

---

### mapping.json（核心配置）

**位置：**
- `userspace/data_source/mapping.py` - **核心配置文件（必需）**，需定义 `DATA_SOURCES`；兼容旧版 `mapping.json`

**职责：**
- 定义 data source 到 handler 的映射关系
- 配置 Provider 的 API 调用信息
- **可选**：覆盖 Handler 的默认配置（通过 `handler_config`）

**配置结构：**

```json
{
  "data_sources": {
    "gdp": {
      "handler": "userspace.data_source.handlers.gdp.GdpHandler",
      "is_enabled": true,
      "dependencies": {},
      "provider_config": {
        "apis": [
          {
            "provider_name": "tushare",
            "method": "get_gdp",
            "field_mapping": {
              "quarter": "quarter",
              "gdp": "gdp",
              "gdp_yoy": "gdp_yoy"
            },
            "params": {},
            "depends_on": []
          }
        ]
      },
      "handler_config": {
        "rolling_periods": 8
      }
    }
  }
}
```

**字段说明：**
- `handler` - Handler 类的完整路径（必需，如 `"userspace.data_source.handlers.kline.KlineHandler"`）
- `is_enabled` - 是否启用（可选，默认为 `true`）
- `dependencies` - 依赖关系声明（可选，如 `{"stock_list": true, "latest_completed_trading_date": false}`）
- `provider_config` - Provider 配置（必需）
  - `apis` - API 配置列表（每个 API 包含 `provider_name`、`method`、`field_mapping`、`params`、`depends_on` 等）
- `handler_config` - Handler 特定配置（可选，用于覆盖 JSON 配置文件中的默认值）

**注意：**
- `handler_config` 是可选的，如果 Handler 有 JSON 配置文件，JSON 配置会作为默认值
- `mapping.json` 中的 `handler_config` 会覆盖 JSON 配置和 Config 类的默认值

---

### Handler 配置文件（config.json）

**位置：**
- `userspace/data_source/handlers/{handler_name}/config.json` - **Handler 默认配置（可选）**

**职责：**
- 定义 Handler 的默认配置（"出厂设置"）
- 提供类型安全的配置管理（通过 Config 数据类）

**配置示例：**

```json
{
  "_comment": "GDP Handler 默认配置",
  "date_format": "quarter",
  "default_date_range": {
    "years": 5
  },
  "rolling_periods": 4
}
```

**配置读取逻辑：**
1. 系统会自动从 `handlers/{handler_name}/config.json` 读取配置
2. 如果文件不存在，使用 Config 类的默认值
3. `mapping.json` 中的 `handler_config` 会覆盖 JSON 配置

**字段说明：**
- 所有字段都继承自 `BaseHandlerConfig`
- 可以包含业务特定的字段（如果 Handler 定义了自定义 Config 类）
- 字段类型和默认值由 Config 数据类定义

**配置加载策略：**
- JSON 配置文件是可选的，如果不存在，使用 Config 类的默认值
- 如果 Handler 没有定义 `config_class`，系统会跳过 Config 类创建，直接使用 `mapping.json` 中的配置

---

## 🚀 基本用法

### 1. 初始化 DataSourceManager

```python
from core.modules.data_source.data_source_manager import DataSourceManager

# 初始化
manager = DataSourceManager(is_verbose=False)
```

### 2. 执行数据更新

```python
# 执行所有启用的 handler（配置驱动）
await manager.renew_data(
    latest_completed_trading_date="20251222",  # 可选，不提供则自动获取
    stock_list=None,  # 可选，不提供则从数据库读取
    test_mode=False,  # 测试模式，只处理前 10-20 个股票
    dry_run=False  # 干运行模式，不写入任何数据
)
```

### 3. 测试单个 Handler（测试用 API）

```python
# 测试单个 handler（需要 handler 在 mapping.json 中启用）
result = await manager.fetch(
    "kline",
    context={
        "latest_completed_trading_date": "20251222",
        "stock_list": ["000001.SZ", "000002.SZ"]
    }
)
```

**注意：**
- `fetch()` 方法会检查 `is_enabled` 配置
- 如果 handler 被禁用，会抛出 `ValueError`

---

> 💡 **提示**：详细的运行时 Workflow 和 renew_data 执行流程请参考 [架构文档](../../../docs/architecture/core_modules/data_source/architecture.md)。

---

## 📚 相关文档

- [架构文档](../../../docs/architecture/core_modules/data_source/architecture.md) - 架构文档，包含运行时 Workflow、Entity 职责、重要决策记录等
- [用户自定义区域 README](../../../userspace/data_source/README.md) - 用户自定义 Handler 和 Provider 的指南

---

## 💡 使用建议

### 何时使用 SimpleConfigHandler？

如果你需要：
- ✅ 简单的单 API 调用
- ✅ 字段映射
- ✅ 滚动刷新或全量刷新

那么使用 `SimpleConfigHandler` 即可，无需编写代码。

### 何时需要自定义 Handler？

如果你需要：
- ✅ 多个 API 协作
- ✅ 复杂的业务逻辑
- ✅ 自定义的数据处理流程
- ✅ 特殊的数据合并逻辑

那么需要创建自定义 Handler，继承 `BaseDataSourceHandler`。

### 最佳实践

1. **配置优先**：尽量使用配置而非代码来实现功能
2. **职责清晰**：Provider 只负责 API 封装，Handler 负责业务逻辑
3. **测试友好**：Handler 的 `fetch()` 和 `normalize()` 方法应该易于测试
4. **错误处理**：在 Handler 中实现适当的错误处理和日志记录

---

**版本：** 3.0  
**维护者：** @garnet  
**最后更新：** 2026-01-XX
