# Data Source 架构设计文档

**版本：** 2.0  
**日期：** 2025-12-19  
**状态：** 生产环境

---

## 📋 目录

1. [设计背景](#设计背景)
2. [核心设计思想](#核心设计思想)
3. [架构设计](#架构设计)
4. [Handler 设计](#handler-设计)
5. [依赖注入架构](#依赖注入架构)
6. [基础类设计](#基础类设计)
7. [实施历史](#实施历史)

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
STOCK_LIST = DataSourceSchema(
    name="stock_list",
    schema={...}
)

# 用户：根据手里的 Provider 自由实现 Handler
class MyHandler(BaseDataSourceHandler):
    data_source = "stock_list"
    
    async def fetch(self, context):
        # 完全由用户控制
        return {...}
```

### 2. 一个 dataSource，多个 handler

```python
# 可以有多个 handler 实现
# - defaults.handlers.stock_list.TushareStockListHandler
# - custom.handlers.stock_list.MyStockListHandler

# 通过 mapping.json 选择使用哪个
{
    "stock_list": {
        "handler": "defaults.handlers.stock_list.TushareStockListHandler"
    }
}
```

### 3. 配置驱动，灵活切换

```json
// custom/mapping.json
{
    "data_sources": {
        "stock_list": {
            "handler": "defaults.handlers.stock_list.TushareStockListHandler",
            "is_enabled": true,
            "dependencies": {
                "latest_completed_trading_date": false,
                "stock_list": false
            },
            "params": {}
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
- ❌ 全局限流管理（由 Manager 负责）

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

### 关键设计决策

| 功能 | 定义位置 | 执行位置 | 理由 |
|-----|---------|---------|------|
| **API 限流信息** | Provider（类属性） | Handler | Provider 只声明元信息 |
| **限流执行** | Utils（RateLimiter） | Handler | Handler 负责限流逻辑 |
| **多线程调度** | Manager | Manager | 全局视角，运行所有 enabled handler |
| **批量处理** | Handler | Handler | 业务逻辑决定 |
| **数据标准化** | Handler | Handler | 业务逻辑 |
| **依赖处理** | Handler | Handler | Handler 自己解决依赖 |
| **认证配置** | Provider | Provider | 基础设施 |
| **Provider 注入** | mapping.json | Manager | 配置驱动，灵活切换 |
| **全局依赖注入** | Manager | Manager | 统一管理，确保一致性 |

---

## Handler 设计

### Handler 生命周期

```
execute(context)
  ↓
before_fetch(context)  # 数据准备阶段，构建执行上下文
  ↓
fetch(context) → List[DataSourceTask]  # 生成 Tasks（包含多个 ApiJobs）
  ↓
after_fetch(tasks, context)  # Tasks 生成后（还未执行）
  ↓
框架执行 Tasks（TaskExecutor）
  ├─ 拓扑排序（根据 depends_on）
  ├─ 获取限流信息（从 Provider）
  ├─ 决定线程数
  └─ 按阶段执行
  ↓
before_normalize(raw_data)  # 标准化前
  ↓
normalize(raw_data) → Dict  # 标准化数据
  ↓
after_normalize(normalized_data)  # 标准化后，通常用于保存数据
```

### Handler 接口

```python
class BaseDataSourceHandler(ABC):
    # 类属性（元信息）
    data_source: str                # 数据源名称
    description: str                 # 描述
    dependencies: List[str]         # 依赖的其他数据源
    
    # 核心方法
    async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
        """生成 Tasks（包含多个 ApiJobs）"""
        pass
    
    async def normalize(self, raw_data: Dict) -> Dict:
        """标准化数据"""
        pass
    
    # 钩子方法
    async def before_fetch(self, context: Dict[str, Any]):
        """数据准备阶段，构建执行上下文"""
        pass
    
    async def after_fetch(self, tasks: List[DataSourceTask], context: Dict[str, Any]):
        """Tasks 生成后（还未执行）"""
        pass
    
    async def before_normalize(self, raw_data: Any):
        """标准化前"""
        pass
    
    async def after_normalize(self, normalized_data: Dict):
        """标准化后，通常用于保存数据"""
        pass
    
    async def on_error(self, error: Exception, context: Dict[str, Any]):
        """错误处理"""
        pass
```

### Task 和 ApiJob 设计

**设计理念：**
- **ApiJob**：单个 API 调用任务（最小执行单元）
- **DataSourceTask**：业务任务（包含多个 ApiJobs，代表一个完整的数据处理流程）

**好处：**
- **更直观**：一个 Task 代表一个业务任务（如"获取复权因子"），可以完整看到数据处理流程
- **更易理解**：不需要读很多代码就能理解一个 Task 包含哪些 API 调用
- **更易维护**：针对一只股票或一个日期产生的多个 API 调用，都在一个 Task 中

**ApiJob 定义：**
```python
@dataclass
class ApiJob:
    provider_name: str           # Provider 名称
    method: str                  # Provider 方法名
    params: Dict[str, Any]       # 调用参数（已计算好）
    depends_on: List[str] = []   # 依赖的 ApiJob ID 列表
    job_id: Optional[str] = None  # Job ID（用于依赖关系）
    api_name: Optional[str] = None  # API 名称（用于限流）
```

**DataSourceTask 定义：**
```python
@dataclass
class DataSourceTask:
    task_id: str                 # Task ID（唯一标识）
    api_jobs: List[ApiJob]        # 包含的 ApiJobs 列表
    description: Optional[str] = None  # Task 描述
```

---

## 依赖注入架构

### 设计目标

1. **统一依赖管理**：在 `renew_data` 开始时统一解析和获取所有需要的全局依赖
2. **按需获取**：只获取真正需要的依赖，避免不必要的开销
3. **配置驱动**：通过 `mapping.json` 显式声明每个 handler 的依赖需求
4. **易于扩展**：预留接口，方便未来添加新的全局依赖
5. **状态隔离**：context 只在 `renew_data` 方法内存在，方法执行完自动销毁

### 架构层次

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

### mapping.json 扩展

在 `mapping.json` 中为每个 handler 添加 `dependencies` 字段：

```json
{
  "data_sources": {
    "kline": {
      "handler": "defaults.handlers.kline.KlineHandler",
      "is_enabled": true,
      "dependencies": {
        "latest_completed_trading_date": true,
        "stock_list": true
      },
      "params": {}
    },
    "gdp": {
      "handler": "defaults.handlers.rolling.RollingHandler",
      "is_enabled": true,
      "dependencies": {
        "latest_completed_trading_date": false,
        "stock_list": false
      },
      "params": {...}
    }
  }
}
```

**依赖声明规则：**
1. **显式声明**：每个 handler 必须显式声明所有依赖（即使为 `false`）
2. **布尔值**：`true` 表示需要，`false` 表示不需要
3. **默认值**：如果某个 handler 没有 `dependencies` 字段，默认所有依赖都为 `false`
4. **向后兼容**：现有 handler 如果没有声明依赖，框架会按需获取（保留兜底逻辑）

### 依赖获取器注册

```python
# 在 DataSourceManager 类中定义
_DEPENDENCY_FETCHERS = {
    "latest_completed_trading_date": lambda dm: dm.service.calendar.get_latest_completed_trading_date(),
    "stock_list": lambda dm: dm.load_stock_list(filtered=True),
    # 未来可以添加：
    # "market_status": lambda dm: dm.get_market_status(),
    # "trading_calendar": lambda dm: dm.get_trading_calendar(),
}
```

---

## 基础类设计

### BaseProvider（基础设施层）

**设计原则：**
1. **纯 API 封装** - 不包含业务逻辑
2. **声明式元数据** - 限流、认证信息作为类属性
3. **简单可测试** - 每个方法只做一件事

**职责：**
- ✅ 封装第三方 API 调用
- ✅ 声明 API 限流信息（不执行）
- ✅ 认证配置和验证
- ✅ 错误转换（统一错误格式）
- ❌ 不包含业务逻辑
- ❌ 不执行限流逻辑
- ❌ 不处理数据标准化

**类结构：**
```python
class BaseProvider(ABC):
    # 类属性（元信息）
    provider_name: str              # Provider 名称
    requires_auth: bool             # 是否需要认证
    auth_type: str                  # 认证类型
    api_limits: Dict[str, int]      # API 限流声明
    default_rate_limit: int         # 默认限流
    
    # 方法
    __init__(config)                # 初始化
    _initialize()                   # 子类实现
    get_api_limit(api_name)         # 获取限流信息
    get_metadata()                  # 获取元信息
    handle_error(error, api_name)   # 错误处理
```

### BaseDataSourceHandler（业务逻辑层）

**设计原则：**
1. **fetch + normalize 分离** - 职责清晰
2. **模板方法模式** - 统一流程，灵活扩展
3. **元信息自描述** - 类属性声明特性

**职责：**
- ✅ 调用 Provider 获取数据
- ✅ 数据标准化（转为 schema 格式）
- ✅ 多 Provider 组合
- ✅ 依赖数据处理
- ✅ 批量处理逻辑
- ❌ 不包含多线程调度（由 Manager 负责）
- ❌ 不包含全局限流管理（由 Manager 负责）

**类结构：**
```python
class BaseDataSourceHandler(ABC):
    # 类属性（元信息）
    data_source: str                # 数据源名称
    description: str                # 描述
    dependencies: List[str]         # 依赖
    
    # 核心方法
    async def fetch(self, context) -> List[DataSourceTask]:
        """生成 Tasks"""
        pass
    
    async def normalize(self, raw_data) -> Dict:
        """标准化数据"""
        pass
    
    async def execute(self, context) -> Dict:
        """完整流程（模板方法）"""
        # before_fetch → fetch → after_fetch
        # → 框架执行 Tasks
        # → before_normalize → normalize → after_normalize
        pass
    
    # 钩子方法
    async def before_fetch(self, context):
        """数据准备阶段，构建执行上下文"""
        pass
    
    async def after_fetch(self, tasks, context):
        """Tasks 生成后"""
        pass
    
    async def before_normalize(self, raw_data):
        """标准化前"""
        pass
    
    async def after_normalize(self, normalized_data):
        """标准化后"""
        pass
    
    async def on_error(self, error, context):
        """错误处理"""
        pass
```

---

## 实施历史

### v1.0（初始版本）

- 基础架构设计
- BaseProvider 和 BaseHandler 实现
- 简单的配置驱动机制

### v2.0（当前版本，2025-12-19）

**主要改进：**

1. **依赖注入架构**
   - 统一依赖管理：在 `renew_data` 开始时统一解析和获取所有需要的全局依赖
   - 按需获取：只获取真正需要的依赖，避免不必要的开销
   - 配置驱动：通过 `mapping.json` 显式声明每个 handler 的依赖需求

2. **Handler 生命周期优化**
   - 重命名 `fetch_and_normalize` → `execute`（更清晰地表示完整生命周期）
   - 优化 `before_fetch` 职责：构建执行上下文（build context）
   - 明确各钩子方法的职责和使用场景

3. **配置深度合并**
   - `custom/mapping.json` 深度合并到 `defaults/mapping.json`
   - `params` 字段深度合并
   - `dependencies` 字段完全覆盖

4. **代码清理**
   - 移除所有硬编码的 `renew_*_data` 方法
   - 完全配置驱动，通过 `mapping.json` 控制 handler 执行
   - 移除向后兼容代码

5. **文档整理**
   - 合并所有文档为 3 个核心文档
   - 统一版本号和设计思路

**关键决策：**
- 保持 `before_fetch` 方法名不变（符合生命周期钩子命名规范）
- 依赖获取器放在 `DataSourceManager` 类内作为私有方法
- Context 只在 `renew_data` 方法内存在，方法执行完自动销毁

---

## 📚 相关文档

- [../README.md](../README.md) - 主要文档，介绍重要概念、entity 和用法
- [../QUICK_START.md](../QUICK_START.md) - 快速开始指南，包含简单的自定义示例
- [../README.md](../README.md) - 主要文档，介绍重要概念、entity 和用法

---

**版本：** 2.0  
**维护者：** @garnet  
**最后更新：** 2025-12-19
