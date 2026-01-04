# DataService 模块

## 📁 目录结构

每个 DataService 都有自己的文件夹，便于组织代码和未来扩展：

```
data_services/
├── __init__.py              # BaseDataService 基类
├── stock/                   # 股票数据服务
│   ├── __init__.py          # 导出 StockDataService
│   ├── stock_data_service.py  # 主服务类
│   ├── stock_queries.py     # 复杂 SQL 查询（可选）
│   ├── stock_helpers.py     # 辅助方法（可选）
│   └── stock_types.py       # 类型定义（可选）
├── macro/                   # 宏观经济服务
│   ├── __init__.py
│   └── macro_data_service.py
├── corporate_finance/       # 财务数据服务
│   ├── __init__.py
│   └── corporate_finance_data_service.py
└── ...
```

## 🎯 设计原则

### 1. 每个 Service 一个文件夹

**原因**：
- 代码量大时，单文件会变得混乱
- 便于按职责拆分（主类、查询、辅助、类型等）
- 结构清晰，易于维护

### 2. 文件拆分策略

**主文件**（必需）：
- `<domain>_data_service.py` - 主服务类，包含核心方法

**可选文件**（按需拆分）：
- `<domain>_queries.py` - 复杂 SQL 查询方法
- `<domain>_helpers.py` - 辅助方法、工具函数
- `<domain>_types.py` - TypedDict、类型定义
- `<domain>_validators.py` - 数据验证逻辑

**拆分时机**：
- 主文件超过 300-500 行时考虑拆分
- 有明确的职责边界时拆分（如查询 vs 辅助）
- 团队协作时，拆分可以减少冲突

### 3. 导入规范

**统一入口**：
```python
# 每个 Service 文件夹的 __init__.py 只导出主类
from .stock_data_service import StockDataService
__all__ = ['StockDataService']
```

**使用方式**：
```python
# DataManager 中导入
from app.core_modules.data_manager.data_services.stock import StockDataService

# 外部使用（通过 DataManager）
stock_service = data_manager.get_data_service('stock')
```

## 📋 业务领域分类

### 已实现
- ✅ **stock** - 股票数据（列表、K线、标签、复权因子）

### 待实现
- ⏳ **macro** - 宏观经济（GDP、CPI、Shibor、LPR）
- ⏳ **corporate_finance** - 财务数据
- ⏳ **investment** - 投资交易（交易记录、操作记录）
- ⏳ **industry** - 行业资金流
- ⏳ **index** - 指数指标
- ⏳ **meta** - 元信息
- ⏳ **<strategy>** - 策略相关数据（策略表 + 基础表联动）

## 🔧 创建新 Service 的步骤

1. **创建文件夹**：
   ```bash
   mkdir app/core_modules/data_manager/data_services/<domain>
   ```

2. **创建主文件**：
   ```python
   # <domain>/<domain>_data_service.py
   from .. import BaseDataService
   
   class <Domain>DataService(BaseDataService):
       def __init__(self, data_manager):
           super().__init__(data_manager)
           # 初始化相关 Model
   ```

3. **创建 __init__.py**：
   ```python
   # <domain>/__init__.py
   from .<domain>_data_service import <Domain>DataService
   __all__ = ['<Domain>DataService']
   ```

4. **在 DataManager 中注册**：
   ```python
   # data_manager.py 的 _init_data_services() 方法
   from app.core_modules.data_manager.data_services.<domain> import <Domain>DataService
   self._data_services['<domain>'] = <Domain>DataService(self)
   ```

## 📝 命名规范

- **文件夹名**：小写，单数（如 `stock`, `macro`）
- **文件名**：`<domain>_data_service.py`（下划线连接）
- **类名**：`<Domain>DataService`（驼峰，首字母大写）
- **方法名**：查询用 `load_xxx`，存储用 `save_xxx`

## 🎯 示例：StockDataService 结构

```
stock/
├── __init__.py                    # 导出 StockDataService
├── stock_data_service.py          # 主类（核心方法）
├── stock_queries.py               # 复杂 SQL 查询（未来按需拆分）
│   └── load_stock_with_kline_join()
└── stock_helpers.py               # 辅助方法（未来按需拆分）
    └── format_stock_data()
```

**当前阶段**：所有代码都在 `stock_data_service.py`，未来按需拆分。

