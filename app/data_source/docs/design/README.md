# Data Provider v2.0

数据提供者模块 - 灵活、简单、强大的数据获取框架

---

## 🎯 核心特性

- ✅ **简单直观**：核心概念只有 3 个（DataType、Handler、Manager）
- ✅ **极致灵活**：用户完全控制数据获取逻辑
- ✅ **多实现共存**：一个 DataType 可以有多个 Handler
- ✅ **运行时切换**：随时切换 Handler，方便 A/B 测试
- ✅ **工具化协调器**：可选工具（不强制）
- ✅ **易于扩展**：添加新 DataType 或 Handler 不影响现有代码

---

## 📋 快速开始

### 安装

```bash
cd /Users/garnet/Desktop/stocks-py
source venv/bin/activate
```

### 基本使用

```python
from app.data_provider.core.manager import DataProviderManager
from app.data_provider.handlers.tushare_handler import TushareKlineHandler

# 1. 创建管理器
manager = DataProviderManager(data_manager=my_data_manager)

# 2. 注册默认 DataType
manager.register_defaults()

# 3. 创建并注册 Handler
handler = TushareKlineHandler(
    data_type=manager.get_data_type("stock_kline_daily"),
    provider=my_tushare_provider,
    rate_limiter=my_rate_limiter
)

manager.register_handler(
    "stock_kline_daily", 
    "tushare", 
    handler,
    set_as_active=True
)

# 4. 执行数据获取
result = await manager.renew(
    "stock_kline_daily",
    context={"end_date": "20250101", "ts_code": "000001.SZ"}
)
```

---

## 📊 架构概览

```
用户层：定义 Handler（根据手里的 Provider 自由组合）
    ↓
框架层：
  - DataType（定义 Schema）
  - DataHandler（接口）
  - DataProviderManager（管理和执行）
    ↓
可选工具：
  - DependencyCoordinator（依赖协调）
  - CompositeHandler（组合多个 Provider）
  - RateLimiter（限流）
```

---

## 📂 目录结构

```
app/data_provider/
├── core/
│   ├── data_type.py           # DataType 定义（Schema）
│   ├── handler.py             # DataHandler 接口
│   └── manager.py             # DataProviderManager
│
├── handlers/                   # 默认 Handler 实现
│   ├── tushare_handler.py
│   └── akshare_handler.py
│
├── utils/                      # 可选工具
│   ├── coordinator.py         # 依赖协调器
│   ├── composite_handler.py   # 组合 Handler
│   ├── rate_limiter.py        # 限流工具
│   └── merger.py              # 数据合并工具
│
├── DESIGN_V2.md               # 详细设计文档 ⭐
└── README.md                  # 本文件
```

---

## 📖 文档

- **[DESIGN_V2.md](./DESIGN_V2.md)** - 完整设计文档（必读）
  - 架构设计
  - 核心组件
  - 使用示例
  - 可选工具
  - 实施计划

---

## 🚀 实施状态

| 阶段 | 状态 | 说明 |
|-----|------|------|
| **Phase 1** | ⏳ 待开始 | 核心实现（DataType + Handler + Manager）|
| **Phase 2** | ⏳ 待开始 | 默认 Handler 实现 |
| **Phase 3** | ⏳ 待开始 | 可选工具 |
| **Phase 4** | ⏳ 待开始 | 文档和示例 |

---

## 💡 核心设计思想

### 1. 框架只定义准则，用户控制实现

```python
# 框架：定义 DataType Schema
STOCK_KLINE_DAILY = DataType(
    name="stock_kline_daily",
    schema={
        "ts_code": Field(str, required=True),
        "trade_date": Field(str, required=True),
        "open": Field(float, required=True),
        # ...
    }
)

# 用户：根据手里的 Provider 自由实现 Handler
class MyHandler(DataHandler):
    async def fetch_and_normalize(self, context):
        # 完全由用户控制
        return {...}
```

### 2. 一个 DataType，多个 Handler

```python
# 注册多个 Handler
manager.register_handler("stock_kline_daily", "tushare", tushare_handler)
manager.register_handler("stock_kline_daily", "akshare", akshare_handler)

# 运行时选择
manager.set_active_handler("stock_kline_daily", "tushare")

# 或临时切换
result = await manager.renew("stock_kline_daily", context, handler_name="akshare")
```

### 3. 工具化协调器（可选使用）

```python
# 简单场景：直接用 Handler
result = await manager.renew("stock_kline_daily", context)

# 复杂场景：使用可选工具
coordinator = DependencyCoordinator(manager)
coordinator.register_dependency("adj_factor", ["stock_kline_daily"])
result = await coordinator.renew_with_dependencies("adj_factor", context)
```

---

## 🤝 贡献指南

### 添加新 DataType

```python
from app.data_provider.core.data_type import DataType, Field

# 1. 定义 DataType
my_data_type = DataType(
    name="my_custom_data",
    schema={"field1": Field(str, required=True), ...}
)

# 2. 注册
manager.register_data_type(my_data_type)
```

### 添加新 Handler

```python
from app.data_provider.core.handler import DataHandler

# 1. 实现 Handler
class MyHandler(DataHandler):
    async def fetch_and_normalize(self, context):
        # 实现数据获取和标准化逻辑
        return {...}

# 2. 注册
manager.register_handler("my_custom_data", "my_handler", MyHandler(...))
```

详见 [DESIGN_V2.md](./DESIGN_V2.md)

---

**版本：** 2.0  
**维护者：** @garnet  
**最后更新：** 2025-12-08

