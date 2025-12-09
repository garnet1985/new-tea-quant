# Data Source 架构设计文档索引

数据源模块 - 灵活、简单、强大的数据获取框架

---

## 🎯 核心特性

- ✅ **简单直观**：核心概念只有 4 个（dataSource、schema、handler、provider）
- ✅ **极致灵活**：用户完全控制数据获取逻辑
- ✅ **多实现共存**：一个 dataSource 可以有多个 handler
- ✅ **运行时切换**：通过配置文件切换 handler，无需修改代码
- ✅ **易于扩展**：添加新 dataSource 或 handler 不影响现有代码

---

## 📋 快速开始

### 基本使用

```python
from app.data_source.data_source_manager import DataSourceManager

# 1. 创建管理器
manager = DataSourceManager(data_manager=my_data_manager)

# 2. 执行数据获取（自动使用配置的 handler）
result = await manager.renew(
    "stock_list",
    context={"end_date": "20250101"}
)
```

---

## 📊 架构概览

```
用户层：定义 Handler（根据手里的 Provider 自由组合）
    ↓
框架层：
  - dataSource（业务需求）
  - schema（数据格式规范）
  - handler（实现方式）
  - provider（基础设施）
    ↓
Manager 层：
  - 配置加载和注册
  - 运行所有 enabled 的 handler
```

---

## 📂 目录结构

```
app/data_source/
├── __init__.py
├── base_handler.py                # Handler 基类
├── base_provider.py               # Provider 基类
├── data_source_manager.py         # 主入口
│
├── defaults/                      # 框架默认（只读）
│   ├── schemas.py                 # 默认 schema 定义
│   ├── handlers/                  # 默认 handler 实现
│   ├── mapping.json               # 默认配置
│   └── README.md
│
├── custom/                        # 用户自定义（完全控制）
│   ├── schemas.py                 # 用户自定义 schema
│   ├── handlers/                 # 用户自定义 handler
│   ├── mapping.json               # 用户配置（核心）
│   └── README.md
│
├── providers/                     # Provider 封装
│   ├── tushare/
│   └── akshare/
│
├── utils/                         # 工具类（可选）
│   ├── coordinator.py
│   ├── rate_limiter.py
│   └── merger.py
│
└── docs/
    └── design/
        ├── DESIGN_V2.md           # 完整设计文档 ⭐
        ├── BASE_CLASSES.md        # 基础类文档
        └── README.md              # 本文件
```

---

## 📖 文档

- **[DESIGN_V2.md](./DESIGN_V2.md)** - 完整设计文档（必读）
  - 核心概念
  - 架构设计
  - 职责划分
  - 使用示例
  - 实施计划

- **[BASE_CLASSES.md](./BASE_CLASSES.md)** - 基础类设计文档
  - BaseProvider 设计
  - BaseHandler 设计
  - 职责总结

---

## 🎯 核心设计思想

### 1. 框架定义准则，用户控制实现

```python
# 框架：定义 dataSource 和 schema
STOCK_LIST = DataSourceSchema(
    name="stock_list",
    schema={...}
)

# 用户：根据手里的 Provider 自由实现 Handler
class MyHandler(BaseHandler):
    data_source = "stock_list"
    renew_type = "refresh"
    
    async def fetch(self, context):
        # 完全由用户控制
        return {...}
```

### 2. 一个 dataSource，多个 handler

```python
# 可以有多个 handler 实现
# - defaults.handlers.stock_list_handler.TushareStockListHandler
# - custom.handlers.stock_list_handler.MyStockListHandler

# 通过 mapping.json 选择使用哪个
{
    "stock_list": {
        "handler": "defaults.handlers.stock_list_handler.TushareStockListHandler"
    }
}
```

### 3. 配置驱动，灵活切换

```json
// custom/mapping.json
{
    "data_sources": {
        "stock_list": {
            "handler": "defaults.handlers.stock_list_handler.TushareStockListHandler",
            "is_enabled": true,
            "params": {
                "providers": {
                    "tushare": {"token": "your_token"}
                }
            }
        }
    }
}
```

---

## 🔑 关键设计决策

| 功能 | 职责归属 | 说明 |
|-----|---------|------|
| **依赖处理** | Handler | Handler 自己解决依赖 |
| **限流执行** | Handler | Handler 负责限流逻辑 |
| **多线程调度** | Manager | Manager 运行所有 enabled 的 handler |
| **Provider 注入** | 配置 | 通过 mapping.json 配置 Provider |

---

## 🚀 实施状态

| 阶段 | 状态 | 说明 |
|-----|------|------|
| **Phase 1** | ✅ 完成 | 基础类设计（BaseProvider、BaseHandler） |
| **Phase 2** | ⏳ 待开始 | DataSourceManager 实现 |
| **Phase 3** | ⏳ 待开始 | 默认 Handler 实现 |
| **Phase 4** | ⏳ 待开始 | 工具类和文档完善 |

---

**版本：** 2.0  
**维护者：** @garnet  
**最后更新：** 2025-12-08
