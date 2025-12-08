# Data Source 架构设计文档 v2.0

**版本：** 2.0  
**日期：** 2025-12-08  
**状态：** 最终设计

---

## 📋 核心概念

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

---

### 1. dataSource（数据源）

**定义：** 框架运行时需要的一种数据

**示例：**
- `stock_list` - 股票列表
- `daily_kline` - 日线数据
- `central_bank_rate` - 央行利率
- `corporate_finance` - 财务数据

**职责：**
- 业务概念，定义"我们需要什么数据"
- 与技术实现无关

**特点：**
- 业务导向
- 一个 dataSource 对应唯一的 schema

---

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

---

### 3. handler（获取方法定义）

**定义：** 获取 dataSource 的方法定义入口

**职责：**
- 实现层，定义"如何"获取数据
- 组合一个或多个 provider
- 处理 provider 之间的依赖关系
- 将原始数据标准化为符合 schema 的格式

**示例：**
```python
class MyStockListHandler:
    """使用 Tushare 获取股票列表"""
    
    async def fetch_and_normalize(self, context):
        # 1. 使用 Tushare provider 获取主要数据
        raw_data = await self.tushare_provider.get_stock_list()
        
        # 2. 使用 AKShare provider 补充某些字段（可选）
        supplement = await self.akshare_provider.get_extra_info()
        
        # 3. 合并数据
        merged = self.merge(raw_data, supplement)
        
        # 4. 标准化为框架 schema
        normalized = self.normalize_to_schema(merged)
        
        return normalized
```

**特点：**
- 用户自定义，可以有无数个
- 一个 dataSource 可以有多个 handler（不同实现方式）
- **运行时只选择一个 handler**
- handler 内部可能非常复杂（多个 provider、依赖、限流、错误处理等）

---

### 4. provider（数据提供方）

**定义：** 纯第三方的数据框架/数据源

**示例：**
- Tushare
- AKShare
- Wind
- Bloomberg

**职责：**
- 基础设施，提供原始数据
- 与框架无关，只是数据来源

**特点：**
- 第三方，不受框架控制
- 一个 handler 可能用到多个 provider
- provider 之间可能有依赖关系
- 返回的数据格式各不相同（需要 handler 标准化）

---

## 🎯 职责总结表

| 概念 | 层次 | 职责 | 数量 | 示例 |
|-----|------|------|------|------|
| **dataSource** | 业务层 | 定义需要什么数据（"要什么"）| 多个 | stock_list, daily_kline |
| **schema** | 规范层 | 定义数据格式要求（"什么格式"）| 每个 dataSource 一个 | ts_code, name, list_date |
| **handler** | 实现层 | 定义如何获取数据（"怎么获取"）| 每个 dataSource 可以多个 | TushareHandler, CompositeHandler |
| **provider** | 基础设施 | 提供原始数据（"从哪获取"）| 多个 | Tushare, AKShare, Wind |

---

## 🏛️ 架构职责划分

### 三层架构

```
┌─────────────────────────────────────────────────┐
│         DataSourceManager (协调层)               │
│  - 加载配置和注册                                 │
│  - 全局多线程调度                                 │
│  - 全局限流管理                                   │
│  - 进度跟踪                                      │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │   Handler (业务层)  │
         │  - 数据获取逻辑      │
         │  - 数据标准化        │
         │  - 多 Provider 组合  │
         │  - 依赖处理          │
         │  - 批量处理逻辑      │
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

**设计原则：**
```python
class TushareProvider(BaseProvider):
    provider_name = "tushare"
    requires_auth = True
    auth_type = "token"
    
    # 只声明限流信息，不执行
    api_limits = {
        "get_daily_kline": 100,   # 每分钟100次
        "get_weekly_kline": 50,   # 每分钟50次
    }
    
    # 简单的 API 封装
    def get_daily_kline(self, ts_code, start_date, end_date):
        return self.api.daily(ts_code=ts_code, ...)
```

#### Handler 层（业务逻辑）

**应该包含：**
- ✅ 数据获取逻辑（调用 Provider）
- ✅ 数据标准化（转为框架 schema）
- ✅ 多 Provider 组合和协调
- ✅ 依赖数据处理
- ✅ 批量处理逻辑
- ✅ Handler 元信息（renew_type, dependencies）

**不应包含：**
- ❌ 多线程调度（由 Manager 负责）
- ❌ 全局限流管理（由 Manager 负责）

**设计原则：**
```python
class TushareStockListHandler(BaseHandler):
    data_source = "stock_list"
    renew_type = "refresh"
    dependencies = []
    
    async def fetch(self, context):
        # 获取原始数据
        provider = self.get_provider("tushare")
        return provider.get_stock_list()
    
    async def normalize(self, raw_data):
        # 标准化为 schema
        return {"stocks": [...]}
```

#### Manager 层（协调管理）

**应该包含：**
- ✅ 配置加载和 Handler 注册
- ✅ 全局多线程调度
- ✅ 全局限流执行（根据 Provider 声明）
- ✅ 进度跟踪
- ✅ 错误汇总

**不应包含：**
- ❌ 具体的数据获取逻辑
- ❌ 数据标准化逻辑

### 关键设计决策

| 功能 | 定义位置 | 执行位置 | 理由 |
|-----|---------|---------|------|
| **API 限流信息** | Provider（类属性） | Manager/Executor | Provider 只声明元信息 |
| **限流执行** | Utils（RateLimiter） | Manager | 全局协调，避免冲突 |
| **多线程调度** | Manager | Manager | 全局视角，统一管理 |
| **批量处理** | Handler | Handler | 业务逻辑决定 |
| **数据标准化** | Handler | Handler | 业务逻辑 |
| **认证配置** | Provider | Provider | 基础设施 |

---

## 🏗️ 文件结构设计

### 完整结构

```
app/data_source/
├── __init__.py
├── data_source_manager.py         # 主入口（加载 defaults + custom）
├── base_handler.py                # Handler 基类（接口定义）
│
├── defaults/                      # 框架默认（只读）⭐
│   ├── __init__.py
│   ├── schemas.py                 # 默认 dataSource schema 定义
│   │   # 包含所有默认 schema:
│   │   # - STOCK_LIST
│   │   # - DAILY_KLINE, WEEKLY_KLINE, MONTHLY_KLINE
│   │   # - CORPORATE_FINANCE
│   │   # - GDP, CPI, PPI, PMI
│   │   # - SHIBOR, LPR
│   │   # - ...
│   │
│   ├── handlers/                  # 默认 handler 实现
│   │   ├── __init__.py
│   │   ├── stock_list_handler.py
│   │   ├── kline_handler.py
│   │   ├── finance_handler.py
│   │   └── macro_handler.py
│   │
│   └── README.md                  # 说明默认提供了什么
│
├── custom/                        # 用户自定义（完全控制）⭐
│   ├── __init__.py
│   ├── schemas.py                 # 用户自定义 schema（可选）
│   ├── handlers/                  # 用户自定义 handler
│   │   ├── __init__.py
│   │   └── .gitkeep              # 占位文件
│   │
│   ├── mapping.json               # ⭐ 用户配置（决定使用哪个 handler）
│   ├── mapping.example.json       # 配置示例
│   └── README.md                  # 说明用户如何自定义
│
├── providers/                     # Provider 封装（基础设施）
│   ├── __init__.py
│   ├── tushare/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   └── config.py
│   ├── akshare/
│   │   └── provider.py
│   └── ...
│
├── utils/                         # 工具类
│   ├── __init__.py
│   ├── coordinator.py            # 依赖协调器（可选）
│   ├── rate_limiter.py           # 限流工具
│   └── merger.py                 # 数据合并工具
│
└── docs/
    └── design/
        └── DESIGN_V2.md          # 本文档
```

---

### defaults/ 文件夹（框架默认，只读）

**说明：**
- 包含框架默认提供的 schema 和 handler
- **不应修改**
- 用户可以在 `custom/mapping.json` 中选择使用

**内容：**
- `schemas.py` - 所有默认 dataSource 的 schema 定义
- `handlers/` - 所有默认 handler 实现
- `README.md` - 说明默认提供了什么

---

### custom/ 文件夹（用户自定义，完全控制）

**说明：**
- 用户完全控制此文件夹
- 可以添加自定义 schema、handler
- 可以修改 `mapping.json` 切换 handler

**内容：**
- `schemas.py` - 用户自定义 schema（可选，覆盖默认）
- `handlers/` - 用户自定义 handler
- `mapping.json` - **配置使用哪个 handler（核心配置）**
- `mapping.example.json` - 配置示例
- `README.md` - 使用说明

---

## 📄 配置文件设计

### custom/mapping.json

**格式：**
```json
{
    "data_sources": {
        "stock_list": {
            "handler": "defaults.handlers.stock_list_handler.TushareStockListHandler",
            "type": "refresh",
            "description": "使用默认的 Tushare handler 获取股票列表"
        },
        "daily_kline": {
            "handler": "custom.handlers.my_kline_handler.MyKlineHandler",
            "type": "incremental",
            "description": "使用我自定义的 handler 获取日线数据"
        },
        "central_bank_rate": {
            "handler": "defaults.handlers.macro_handler.CentralBankRateHandler",
            "type": "refresh"
        }
    }
}
```

**说明：**
- `handler`：完整的类路径
  - `defaults.handlers.xxx` - 使用框架默认 handler
  - `custom.handlers.xxx` - 使用用户自定义 handler
- `type`：数据更新类型
  - `refresh` - 全量刷新
  - `incremental` - 增量更新
- `description`：可选说明

---

### custom/mapping.example.json（配置示例）

```json
{
    "_comment": "这是配置示例，复制为 mapping.json 并修改",
    "data_sources": {
        "stock_list": {
            "handler": "defaults.handlers.stock_list_handler.TushareStockListHandler",
            "type": "refresh"
        },
        "daily_kline": {
            "handler": "defaults.handlers.kline_handler.TushareDailyKlineHandler",
            "type": "incremental"
        }
    }
}
```

---

## 🎯 核心组件设计

### 1. DataSourceSchema（框架层）

**定义：** 数据格式规范

```python
# app/data_source/defaults/schemas.py
from dataclasses import dataclass
from typing import Any, Optional, Callable

@dataclass
class Field:
    """字段定义"""
    type: type
    required: bool = True
    default: Optional[Any] = None
    description: str = ""
    validator: Optional[Callable] = None

class DataSourceSchema:
    """DataSource Schema 定义"""
    
    def __init__(self, name: str, schema: dict, description: str = ""):
        self.name = name
        self.schema = schema
        self.description = description
    
    def validate(self, data: dict) -> bool:
        """验证数据是否符合 schema"""
        for field_name, field_def in self.schema.items():
            # 检查必填字段
            if field_def.required and field_name not in data:
                raise ValueError(f"Required field '{field_name}' missing")
            
            # 检查字段类型
            if field_name in data:
                value = data[field_name]
                if not isinstance(value, field_def.type):
                    raise TypeError(
                        f"Field '{field_name}' type mismatch: "
                        f"expected {field_def.type}, got {type(value)}"
                    )
                
                # 自定义验证器
                if field_def.validator and not field_def.validator(value):
                    raise ValueError(f"Field '{field_name}' validation failed")
        
        return True

# ===== 默认 Schema 定义 =====

STOCK_LIST = DataSourceSchema(
    name="stock_list",
    description="股票列表",
    schema={
        "ts_code": Field(str, required=True, description="股票代码"),
        "symbol": Field(str, required=True, description="股票简称"),
        "name": Field(str, required=True, description="股票名称"),
        "area": Field(str, required=False, description="地域"),
        "industry": Field(str, required=False, description="行业"),
        "list_date": Field(str, required=False, description="上市日期"),
    }
)

DAILY_KLINE = DataSourceSchema(
    name="daily_kline",
    description="日线数据",
    schema={
        "ts_code": Field(str, required=True, description="股票代码"),
        "trade_date": Field(str, required=True, description="交易日期"),
        "open": Field(float, required=True, description="开盘价"),
        "close": Field(float, required=True, description="收盘价"),
        "high": Field(float, required=True, description="最高价"),
        "low": Field(float, required=True, description="最低价"),
        "vol": Field(float, required=True, description="成交量"),
        "amount": Field(float, required=False, description="成交额"),
    }
)

CORPORATE_FINANCE = DataSourceSchema(...)
GDP = DataSourceSchema(...)
CPI = DataSourceSchema(...)
# ...

# 所有默认 Schema
DEFAULT_SCHEMAS = {
    "stock_list": STOCK_LIST,
    "daily_kline": DAILY_KLINE,
    "corporate_finance": CORPORATE_FINANCE,
    "gdp": GDP,
    "cpi": CPI,
    # ...
}
```

---

### 2. BaseHandler（框架定义接口，用户实现）

**定义：** Handler 基类

```python
# app/data_source/base_handler.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseHandler(ABC):
    """
    Handler 基类
    
    用户实现此接口来定义数据获取方法
    
    职责：
    1. 获取原始数据（调用一个或多个 provider）
    2. 处理 provider 之间的依赖关系
    3. 标准化数据（转换为符合 schema 的格式）
    4. 返回标准化后的数据
    """
    
    def __init__(self, schema: 'DataSourceSchema'):
        self.schema = schema
    
    @abstractmethod
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        """
        获取并标准化数据
        
        Args:
            context: 执行上下文，包含：
                - end_date: 截止日期
                - start_date: 开始日期（可选）
                - ts_code: 股票代码（可选）
                - stock_list: 股票列表（可选）
                - custom_params: 自定义参数（可选）
        
        Returns:
            符合 schema 的数据字典
        
        注意：
        - handler 内部可能使用多个 provider
        - handler 需要处理 provider 之间的依赖
        - handler 需要标准化数据为框架 schema
        """
        pass
    
    def validate(self, data: Dict) -> bool:
        """验证数据是否符合 Schema"""
        return self.schema.validate(data)
```

---

### 3. DataSourceManager（框架层）

**定义：** 数据源管理器

```python
# app/data_source/data_source_manager.py
import json
from typing import Dict, Any, Optional
from loguru import logger

class DataSourceManager:
    """
    数据源管理器
    
    职责：
    1. 加载 schema 定义（defaults + custom）
    2. 加载 mapping 配置并动态加载 handler
    3. 执行数据获取
    """
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self._schemas: Dict[str, DataSourceSchema] = {}
        self._handlers: Dict[str, BaseHandler] = {}
        
        # 初始化
        self._load_schemas()
        self._load_mapping()
    
    def _load_schemas(self):
        """加载 schema 定义"""
        # 1. 加载默认 schemas
        from app.data_source.defaults.schemas import DEFAULT_SCHEMAS
        self._schemas.update(DEFAULT_SCHEMAS)
        logger.info(f"✅ Loaded {len(DEFAULT_SCHEMAS)} default schemas")
        
        # 2. 加载用户自定义 schemas（覆盖默认）
        try:
            from app.data_source.custom.schemas import CUSTOM_SCHEMAS
            self._schemas.update(CUSTOM_SCHEMAS)
            logger.info(f"✅ Loaded {len(CUSTOM_SCHEMAS)} custom schemas")
        except ImportError:
            logger.debug("No custom schemas found")
    
    def _load_mapping(self):
        """加载 mapping 配置并动态加载 handler"""
        # 读取用户配置
        with open('app/data_source/custom/mapping.json') as f:
            config = json.load(f)
        
        # 动态加载并实例化 handlers
        for ds_name, ds_config in config['data_sources'].items():
            handler = self._load_handler(
                ds_name, 
                ds_config['handler']
            )
            self._handlers[ds_name] = handler
            logger.info(f"✅ Handler loaded for '{ds_name}'")
    
    def _load_handler(self, ds_name: str, handler_path: str):
        """动态加载 handler"""
        # handler_path 示例:
        # - "defaults.handlers.stock_list_handler.TushareStockListHandler"
        # - "custom.handlers.my_handler.MyHandler"
        
        parts = handler_path.split('.')
        module_path = '.'.join(parts[:-1])
        class_name = parts[-1]
        
        # 动态导入
        module = __import__(
            f'app.data_source.{module_path}', 
            fromlist=[class_name]
        )
        handler_class = getattr(module, class_name)
        
        # 获取 schema
        schema = self._schemas.get(ds_name)
        if not schema:
            raise ValueError(f"Schema for '{ds_name}' not found")
        
        # 实例化（传入 schema 和其他依赖）
        return handler_class(schema, ...)
    
    async def renew(
        self, 
        ds_name: str, 
        context: Dict[str, Any],
        save: bool = True
    ) -> Dict:
        """
        更新数据
        
        Args:
            ds_name: dataSource 名称
            context: 执行上下文（end_date, stock_list 等）
            save: 是否保存数据到数据库
        
        Returns:
            标准化后的数据
        """
        # 1. 获取 handler
        if ds_name not in self._handlers:
            raise ValueError(f"Handler for '{ds_name}' not found")
        
        handler = self._handlers[ds_name]
        
        logger.info(f"🔄 Renewing '{ds_name}'")
        
        # 2. 执行 handler
        data = await handler.fetch_and_normalize(context)
        
        # 3. 验证数据
        schema = self._schemas[ds_name]
        schema.validate(data)
        logger.info(f"✅ Data validated for '{ds_name}'")
        
        # 4. 保存数据（可选）
        if save and self.data_manager:
            await self.data_manager.save(ds_name, data)
            logger.info(f"💾 Data saved for '{ds_name}'")
        
        return data
    
    def list_data_sources(self) -> list:
        """列出所有 dataSource"""
        return list(self._schemas.keys())
    
    def get_schema(self, ds_name: str) -> DataSourceSchema:
        """获取 schema"""
        if ds_name not in self._schemas:
            raise ValueError(f"Schema for '{ds_name}' not found")
        return self._schemas[ds_name]
```

---

## 📋 使用示例

### 示例 1：使用默认 handler

**配置（custom/mapping.json）：**
```json
{
    "data_sources": {
        "stock_list": {
            "handler": "defaults.handlers.stock_list_handler.TushareStockListHandler",
            "type": "refresh"
        }
    }
}
```

**代码：**
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

### 示例 2：用户自定义 handler

**步骤 1：定义自定义 handler**

```python
# custom/handlers/my_kline_handler.py
from app.data_source.base_handler import BaseHandler

class MyKlineHandler(BaseHandler):
    """
    我的自定义 K 线 handler
    
    使用 Tushare 获取主要数据，用 AKShare 补充某些字段
    """
    
    def __init__(self, schema, tushare_provider, akshare_provider, rate_limiter):
        super().__init__(schema)
        self.tushare = tushare_provider
        self.akshare = akshare_provider
        self.limiter = rate_limiter
    
    async def fetch_and_normalize(self, context):
        # 1. 限流
        self.limiter.acquire()
        
        # 2. 使用 Tushare provider 获取主要数据
        raw_data = await self.tushare.daily(
            ts_code=context["ts_code"],
            end_date=context["end_date"]
        )
        
        # 3. 使用 AKShare provider 补充某些字段（可选）
        if context.get("need_supplement"):
            supplement = await self.akshare.get_extra_info(...)
            raw_data = self.merge(raw_data, supplement)
        
        # 4. 标准化为框架 schema
        normalized = {
            "ts_code": raw_data["ts_code"],
            "trade_date": raw_data["trade_date"],
            "open": float(raw_data["open"]),
            "close": float(raw_data["close"]),
            "high": float(raw_data["high"]),
            "low": float(raw_data["low"]),
            "vol": float(raw_data["vol"]),
            "amount": float(raw_data.get("amount", 0)),
        }
        
        # 5. 验证（可选，框架会自动验证）
        self.validate(normalized)
        
        return normalized
```

**步骤 2：配置使用自定义 handler**

```json
// custom/mapping.json
{
    "data_sources": {
        "daily_kline": {
            "handler": "custom.handlers.my_kline_handler.MyKlineHandler",
            "type": "incremental"
        }
    }
}
```

**步骤 3：使用**

```python
# 代码不变，manager 自动使用配置的 handler
result = await manager.renew(
    "daily_kline",
    context={"end_date": "20250101", "ts_code": "000001.SZ"}
)
```

---

### 示例 3：切换 handler

**场景：** 从 Tushare handler 切换到自定义 handler

**操作：** 只需修改 `custom/mapping.json`

```json
{
    "data_sources": {
        "daily_kline": {
            "handler": "defaults.handlers.kline_handler.TushareDailyKlineHandler",
            "type": "incremental"
        }
    }
}
```

**改为：**

```json
{
    "data_sources": {
        "daily_kline": {
            "handler": "custom.handlers.my_kline_handler.MyKlineHandler",
            "type": "incremental"
        }
    }
}
```

**重启应用即可生效，代码无需修改！**

---

## 🎯 设计优势

### 1. 职责清晰

- **dataSource**：业务需求（"要什么"）
- **schema**：技术规范（"什么格式"）
- **handler**：实现方式（"怎么获取"）
- **provider**：基础设施（"从哪获取"）

### 2. 灵活性高

- 用户可以自由定义 handler
- handler 可以组合多个 provider
- 配置文件切换 handler，无需修改代码

### 3. 易于扩展

- 添加新 dataSource：定义 schema + handler
- 添加新 handler：实现接口 + 配置
- 添加新 provider：作为基础设施使用

### 4. 用户友好

- 默认提供常用 dataSource 和 handler
- 用户只需关注 `custom/` 文件夹
- 配置简单，切换方便

---

## 📖 README 文件内容

### defaults/README.md

```markdown
# 默认 DataSource、Schema 和 Handler

本文件夹包含框架默认提供的实现，**不应修改**。

## 默认 DataSource

- `stock_list` - 股票列表
- `daily_kline` - 日线数据
- `weekly_kline` - 周线数据
- `monthly_kline` - 月线数据
- `corporate_finance` - 财务数据
- `gdp` - GDP 数据
- `cpi` - CPI 数据
- ... 

## 使用默认 Handler

在 `custom/mapping.json` 中配置：

```json
{
    "data_sources": {
        "stock_list": {
            "handler": "defaults.handlers.stock_list_handler.TushareStockListHandler"
        }
    }
}
```

## 扩展

如果需要自定义，请在 `custom/` 文件夹中实现。
```

### custom/README.md

```markdown
# 用户自定义区域

本文件夹供用户完全控制，可以自由添加、修改、删除。

## 自定义 Handler

1. 在 `handlers/` 文件夹中创建你的 handler
2. 继承 `BaseHandler` 类
3. 实现 `fetch_and_normalize()` 方法
4. 在 `mapping.json` 中配置使用你的 handler

## 示例

```python
# custom/handlers/my_handler.py
from app.data_source.base_handler import BaseHandler

class MyHandler(BaseHandler):
    async def fetch_and_normalize(self, context):
        # 你的实现
        # 可以使用多个 provider
        # 可以处理复杂的依赖关系
        return data
```

```json
// custom/mapping.json
{
    "data_sources": {
        "stock_list": {
            "handler": "custom.handlers.my_handler.MyHandler"
        }
    }
}
```

## Handler 可以做什么

- 使用一个或多个 provider
- 处理 provider 之间的依赖关系
- 实现限流、重试、缓存等逻辑
- 合并多个数据源的数据
- 标准化数据为框架 schema
```

---

## 📋 实施计划

### Phase 1：核心实现（3-4 天）

```
✅ 核心组件
  - DataSourceSchema
  - BaseHandler
  - DataSourceManager

✅ 默认 Schema 定义
  - stock_list, daily_kline, weekly_kline, monthly_kline
  - corporate_finance
  - gdp, cpi, ppi, pmi, shibor, lpr

✅ 文件结构
  - defaults/ 文件夹
  - custom/ 文件夹
  - mapping.json 配置

✅ 测试
  - 单元测试
  - 集成测试
```

### Phase 2：默认 Handler 实现（3-4 天）

```
✅ Tushare Handler
  - StockListHandler
  - KlineHandler
  - FinanceHandler
  - MacroHandler

✅ 测试
  - Handler 单元测试
  - 集成测试
```

### Phase 3：工具和文档（2-3 天）

```
✅ 工具类
  - 依赖协调器
  - 限流工具
  - 数据合并工具

✅ 文档
  - defaults/README.md
  - custom/README.md
  - mapping.example.json
  - 使用示例
```

---

**最后更新：** 2025-12-08  
**维护者：** @garnet  
**状态：** 最终设计，开始实施
