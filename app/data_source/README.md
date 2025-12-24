# Data Source 模块文档

## 📋 概述

Data Source 模块是一个灵活、简单、强大的数据获取框架，用于统一管理从多个第三方数据源（如 Tushare、AKShare、EastMoney）获取数据的过程。

### 核心特性

- ✅ **简单直观**：核心概念只有 4 个（dataSource、schema、handler、provider）
- ✅ **极致灵活**：用户完全控制数据获取逻辑
- ✅ **多实现共存**：一个 dataSource 可以有多个 handler
- ✅ **运行时切换**：通过配置文件切换 handler，无需修改代码
- ✅ **易于扩展**：添加新 dataSource 或 handler 不影响现有代码
- ✅ **配置驱动**：通过 `mapping.json` 配置 handler 的启用、依赖和参数

---

## 🎯 核心概念

### 层次关系

```
dataSource (框架需要的数据类型)
    ↓ 对应唯一
schema (数据格式规范)
    ↓ 可以有多个实现
handler (获取方法定义)
    ↓ 可能使用多个
provider (第三方数据源)
```

### 1. dataSource（数据源）

**定义：** 框架运行时需要的一种数据

**示例：**
- `stock_list` - 股票列表
- `kline` - K 线数据（日/周/月）
- `corporate_finance` - 企业财务数据
- `gdp` - GDP 数据（季度）
- `cpi` - CPI 价格指数（月度）
- `shibor` - Shibor 利率（日度）

**特点：**
- 业务导向，定义"我们需要什么数据"
- 与技术实现无关
- 一个 dataSource 对应唯一的 schema

### 2. schema（数据格式规范）

**定义：** 框架接受这种数据的统一格式

**职责：**
- 技术规范，定义数据结构、字段、类型
- 验证数据是否符合要求
- 保证数据一致性

**示例：**
```python
STOCK_LIST_SCHEMA = {
    "ts_code": Field(str, required=True, description="股票代码"),
    "symbol": Field(str, required=True, description="股票简称"),
    "name": Field(str, required=True, description="股票名称"),
    "list_date": Field(str, required=False, description="上市日期"),
}
```

**特点：**
- 框架层定义，用户必须遵守
- 一个 dataSource 对应唯一的 schema
- 与获取方式无关

### 3. handler（获取方法定义）

**定义：** 获取 dataSource 的方法定义入口

**职责：**
- 实现层，定义"如何"获取数据
- 组合一个或多个 provider
- 处理 provider 之间的依赖关系
- 将原始数据标准化为符合 schema 的格式

**特点：**
- 用户自定义，可以有无数个
- 一个 dataSource 可以有多个 handler（不同实现方式）
- **运行时只选择一个 handler**
- handler 内部可能非常复杂（多个 provider、依赖、限流、错误处理等）

### 4. provider（数据提供方）

**定义：** 纯第三方的数据框架/数据源

**示例：**
- Tushare
- AKShare
- EastMoney

**职责：**
- 基础设施，提供原始数据
- 与框架无关，只是数据来源

**特点：**
- 第三方，不受框架控制
- 一个 handler 可能用到多个 provider
- provider 之间可能有依赖关系
- 返回的数据格式各不相同（需要 handler 标准化）

---

## 🏗️ 架构组件

### DataSourceManager（数据源管理器）

**职责：**
- 加载 Schema 定义（defaults + custom）
- 加载 Handler 映射配置并动态加载 handler
- 执行数据获取（`renew_data` 方法）
- 管理全局依赖注入（`latest_completed_trading_date`、`stock_list` 等）

**使用示例：**
```python
from app.data_source.data_source_manager import DataSourceManager

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
app/data_source/
├── README.md                       # 主要文档（本文档）
├── QUICK_START.md                  # 快速开始指南
├── __init__.py
├── data_source_manager.py          # 主入口
├── data_source_handler.py          # Handler 基类
├── base_handler.py                 # 简化版 Handler 基类
├── base_provider.py                # Provider 基类
├── api_job.py                      # ApiJob 和 DataSourceTask 定义
├── task_executor.py                # Task 执行器（核心类）
│
├── defaults/                       # 框架默认（只读）
│   ├── schemas.py                  # 默认 schema 定义
│   ├── handlers/                   # 默认 handler 实现
│   │   ├── kline/
│   │   ├── corporate_finance/
│   │   └── ...
│   └── mapping.json                # 默认配置
│
├── custom/                         # 用户自定义（完全控制）
│   ├── schemas.py                  # 用户自定义 schema
│   ├── handlers/                   # 用户自定义 handler
│   └── mapping.json                # 用户配置（核心）
│
├── providers/                      # Provider 封装
│   ├── tushare/
│   ├── akshare/
│   └── eastmoney/
│
└── docs/                           # 设计文档
    └── DESIGN.md                   # 完整设计文档
```

---

## 📄 配置文件

### mapping.json（核心配置）

**位置：**
- `defaults/mapping.json` - 框架默认配置（不应修改）
- `custom/mapping.json` - 用户自定义配置（覆盖默认）

**格式：**
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
      "params": {
        "provider_name": "tushare",
        "method": "get_gdp",
        "date_format": "quarter",
        "rolling_periods": 4
      }
    }
  }
}
```

**字段说明：**
- `handler` - Handler 类的完整路径（必需）
- `is_enabled` - 是否启用（默认 true）
- `dependencies` - 全局依赖声明（`latest_completed_trading_date`、`stock_list`）
- `params` - Handler 自定义参数

**配置合并：**
- `custom/mapping.json` 会深度合并到 `defaults/mapping.json`
- `params` 字段会深度合并
- `dependencies` 字段会完全覆盖（如果 custom 中有声明）

---

## 🚀 基本用法

### 1. 初始化 DataSourceManager

```python
from app.data_source.data_source_manager import DataSourceManager

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

## 📊 数据流程

### renew_data 执行流程

```
renew_data()
  ↓
[Step 1] 依赖解析
  - 读取 mapping.json，找出所有 is_enabled=true 的 handler
  - 收集每个 handler 声明的依赖需求（dependencies）
  - 去重，得到需要获取的全局依赖列表
  ↓
[Step 2] 依赖注入
  - 根据依赖列表，获取所有需要的全局依赖
  - 构建 shared_context（包含 latest_completed_trading_date, stock_list 等）
  - 添加执行参数（test_mode, dry_run 等）
  ↓
[Step 3] Handler 执行
  - 遍历所有启用的 handler
  - 为每个 handler 复制 shared_context，创建独立的 handler_context
  - 调用 handler.execute(handler_context)
    ↓
    before_fetch(context)  # 构建上下文
    fetch(context) → List[DataSourceTask]  # 生成 Tasks
    after_fetch(tasks, context)  # Tasks 生成后
    ↓
    框架执行 Tasks（TaskExecutor）
    ↓
    before_normalize(raw_data)  # 标准化前
    normalize(raw_data) → Dict  # 标准化数据
    after_normalize(normalized_data)  # 标准化后（保存数据）
```

---

## 🔑 关键设计决策

| 功能 | 职责归属 | 说明 |
|-----|---------|------|
| **依赖处理** | Handler | Handler 自己解决依赖 |
| **限流执行** | Handler | Handler 负责限流逻辑 |
| **多线程调度** | Manager | Manager 运行所有 enabled 的 handler |
| **Provider 注入** | 配置 | 通过 mapping.json 配置 Provider |
| **全局依赖注入** | Manager | Manager 统一获取和注入全局依赖 |

---

## 📚 相关文档

- [QUICK_START.md](./QUICK_START.md) - 快速开始指南，包含简单的自定义示例
- [docs/DESIGN.md](./docs/DESIGN.md) - 完整设计文档，包含设计思路、背景和架构

---

**版本：** 2.0  
**维护者：** @garnet  
**最后更新：** 2025-12-19
