# DatabaseManager 直接使用情况分析

## 目标
检查所有直接使用 `DatabaseManager` 实例的类，评估是否可以用 `DataManager` 替换。

## 原则
- `DatabaseManager` 实例应该只由 `DataManager` 持有和管理
- 其他类应该通过 `DataManager` 访问数据，而不是直接使用 `DatabaseManager`
- `DataManager` 是单例，提供统一的数据访问接口

## ✅ 迁移状态总结

**核心模块迁移完成情况**：
- ✅ **BFF API 模块** - 已完成迁移，使用 `DataManager()` 单例
- ✅ **LabelerService** - 已完成迁移，内部使用 `DataManager()` 单例
- ✅ **Analyzer** - 已完成迁移，不再接收 `DatabaseManager` 参数
- ✅ **BaseStrategy** - 已完成迁移，内部使用 `DataManager()` 单例

**迁移原则**：
- 所有业务类不再接收 `db` 或 `data_mgr` 作为参数
- 类内部直接使用 `DataManager()` 单例：`self.data_mgr = DataManager()`
- 表管理操作通过 `self.data_mgr.db` 访问
- 数据访问通过 `self.data_mgr` 的方法进行

---

## 1. 核心模块（需要迁移）

### 1.1 `app/analyzer/analyzer.py` - Analyzer
**当前状态**: ✅ **已完成迁移**
```python
def __init__(self, is_verbose: bool = False):
    self.is_verbose = is_verbose
```

**已完成**:
- ✅ 移除了 `connected_db` 参数，不再接收 `DatabaseManager`
- ✅ 策略类创建时不再传递 `db` 参数
- ✅ 所有策略类内部直接使用 `DataManager()` 单例

**优先级**: ✅ **已完成**

---

### 1.2 `app/analyzer/components/base_strategy.py` - BaseStrategy
**当前状态**: ✅ **已完成迁移**
```python
def __init__(self, is_verbose: bool = False, ...):
    # 统一使用 DataManager 单例作为数据访问入口
    self.data_mgr = DataManager(is_verbose=False)
```

**已完成**:
- ✅ 移除了 `db` 参数，不再接收 `DatabaseManager`
- ✅ 移除了 `self.db`，只保留 `self.data_mgr`
- ✅ `_get_required_tables()` 使用 `DataManager.get_model()` 获取基础表模型
- ✅ `_register_strategy_tables()` 和表创建通过 `self.data_mgr.db` 访问
- ✅ 所有表管理操作都通过 `self.data_mgr.db` 进行

**优先级**: ✅ **已完成**

---

### 1.3 `app/labeler/labeler.py` - LabelerService
**当前状态**: ✅ **已完成迁移**
```python
def __init__(self):
    # 统一使用 DataManager 单例作为数据访问入口
    self.data_mgr = DataManager(is_verbose=False)
```

**已完成**:
- ✅ 移除了 `db` 参数，不再接收 `DatabaseManager`
- ✅ 移除了 `self.db`，只保留 `self.data_mgr`
- ✅ 内部直接使用 `DataManager()` 单例
- ✅ 所有 SQL 查询通过 `self.data_mgr.db.execute_query()` 访问

**优先级**: ✅ **已完成**

---

## 2. BFF API 模块（需要迁移）

### 2.1 `bff/api.py` - BFFApi
**当前状态**: 直接创建 `DatabaseManager`
```python
def __init__(self):
    self.db_manager = DatabaseManager()
    self.db_manager.initialize()
```

**问题**:
- 直接创建 `DatabaseManager` 实例
- 传递给子 API 类

**迁移方案**:
- ✅ 改为使用 `DataManager` 单例
- ✅ 子 API 类接收 `DataManager` 而不是 `DatabaseManager`

**优先级**: 🔴 高

---

### 2.2 `bff/APIs/investment_api.py` - InvestmentApi
**当前状态**: 接收 `db_manager` 作为参数
```python
def __init__(self, db_manager=None):
    self.db_manager = db_manager
```

**问题**:
- 直接持有 `db_manager`
- 在 `_get_*_model()` 方法中使用 `self.db_manager.get_table_instance()` (已修复为使用 DataManager)

**迁移方案**:
- ✅ `_get_*_model()` 已修复，使用 `DataManager.get_model()`
- ✅ 可以改为接收 `DataManager` 或通过单例获取

**优先级**: 🟡 中（部分已修复）

---

### 2.3 `bff/APIs/stock_api.py` - StockApi
**当前状态**: 接收 `db_manager` 作为参数
```python
def __init__(self, db_manager=None):
    self.db_manager = db_manager
```

**问题**:
- 直接持有 `db_manager`
- 可能直接使用 `db_manager` 进行查询

**迁移方案**:
- ✅ 改为接收 `DataManager` 或通过单例获取
- ✅ 使用 `DataManager` 的方法进行数据访问

**优先级**: 🔴 高

---

## 3. DataManager 内部模块（合理使用）

### 3.1 `app/data_manager/data_manager.py` - DataManager
**当前状态**: 持有 `DatabaseManager` 实例
```python
def __init__(self, db: Optional[DatabaseManager] = None, ...):
    self.db = db
```

**说明**: ✅ 这是合理的，`DataManager` 是 `DatabaseManager` 的唯一持有者

**优先级**: ✅ 无需修改

---

### 3.2 `app/data_manager/loaders/*.py` - Loaders
**当前状态**: 接收 `db` 作为参数
```python
def __init__(self, db=None):
    self.db = db
```

**说明**: 
- ⚠️ Loaders 是 `DataManager` 的内部组件
- 它们接收 `db` 是合理的，因为它们是 `DataManager` 的一部分
- 但可以考虑：Loaders 接收 `DataManager` 而不是 `db`，通过 `data_mgr.db` 访问

**优先级**: 🟢 低（内部使用，可以保持现状）

---

### 3.3 `app/data_manager/base_tables/*/model.py` - Models
**当前状态**: 接收 `db` 作为可选参数
```python
def __init__(self, db=None):
    # 如果没有提供 db，使用默认实例
```

**说明**: 
- ✅ Models 使用 `DatabaseManager.get_default()` 获取默认实例
- ✅ 这是合理的，Models 是底层组件，需要直接访问数据库

**优先级**: ✅ 无需修改

---

## 4. Legacy 模块（可以忽略）

### 4.1 `app/data_source_legacy/` - Legacy Data Source
**说明**: 这是旧代码，计划废弃，可以暂时忽略

**优先级**: ⚪ 忽略

---

## 5. 策略类（需要检查）

### 5.1 所有策略类 (`app/analyzer/strategy/*/`)
**当前状态**: 继承 `BaseStrategy`，接收 `db` 参数

**说明**: 
- 策略类通过 `BaseStrategy` 接收 `db`
- 如果 `BaseStrategy` 迁移完成，策略类会自动迁移

**优先级**: 🟡 中（依赖 BaseStrategy 迁移）

---

## 总结

### 需要立即迁移的类（高优先级）:
1. ✅ `app/analyzer/analyzer.py` - Analyzer
2. ✅ `bff/api.py` - BFFApi  
3. ✅ `bff/APIs/stock_api.py` - StockApi

### 部分已迁移的类（中优先级）:
1. ✅ `app/analyzer/components/base_strategy.py` - BaseStrategy (已修复 `_get_required_tables()`)
2. ✅ `bff/APIs/investment_api.py` - InvestmentApi (已修复 `_get_*_model()`)

### 基本已迁移的类（低优先级）:
1. ✅ `app/labeler/labeler.py` - LabelerService (主要使用 `data_mgr`，只需清理 `self.db`)

### 合理的直接使用（无需修改）:
1. ✅ `app/data_manager/data_manager.py` - DataManager (唯一持有者)
2. ✅ `app/data_manager/base_tables/*/model.py` - Models (底层组件)
3. ✅ `app/data_manager/loaders/*.py` - Loaders (内部组件，可选优化)

### 特殊情况说明:

#### BaseStrategy 中的表管理功能
`BaseStrategy` 中仍需要直接访问 `db` 用于：
- `self.db.register_table()` - 注册策略自定义表
- `self.db.create_registered_tables()` - 创建已注册的表
- `self.db.registered_tables` - 访问已注册的表信息
- `self.db.tables` - 访问已创建的表实例

**解决方案**: 
- 策略类可以接收 `DataManager`，通过 `data_mgr.db` 访问 `DatabaseManager`（仅用于表管理）
- 或者：在 `DataManager` 中添加表管理方法，封装这些操作

#### LabelerService 中的直接查询
**状态**: ✅ **已完成迁移**

`LabelerService` 中原本直接使用 `self.db.execute_query()` 进行 SQL 查询的地方：
- `get_label_statistics()` - 已改为 `self.data_mgr.db.execute_query()`
- `get_stock_labels()` - 已改为 `self.data_mgr.db.execute_query()`
- `get_labels_by_date_range()` - 已改为 `self.data_mgr.db.execute_query()`

**已完成**:
- ✅ 所有 SQL 查询现在通过 `self.data_mgr.db` 访问
- ✅ 不再直接持有 `DatabaseManager` 实例
- ⚠️ 注：未来可以考虑将这些 SQL 查询进一步封装到 Model 或 DataService 中

---

### 迁移策略建议:
1. **第一步**: 迁移 BFF API 模块 ✅ **已完成**
   - ✅ 使用 `DataManager` 单例
   - ✅ 子 API 类接收 `DataManager` 而不是 `DatabaseManager`

2. **第二步**: 迁移 LabelerService ✅ **已完成**
   - ✅ 移除 `self.db`，只保留 `self.data_mgr`
   - ✅ 内部直接使用 `DataManager()` 单例
   - ✅ 所有 SQL 查询通过 `self.data_mgr.db` 访问

3. **第三步**: 迁移 Analyzer ✅ **已完成**
   - ✅ 移除 `connected_db` 参数，不再接收 `DatabaseManager`
   - ✅ 策略类创建时不再传递 `db` 参数
   - ✅ 所有策略类内部直接使用 `DataManager()` 单例

4. **第四步**: 优化 BaseStrategy ✅ **已完成**
   - ✅ 移除 `db` 参数，不再接收 `DatabaseManager`
   - ✅ 通过 `self.data_mgr.db` 访问表管理功能
   - ✅ 数据访问全部通过 `DataManager` 的方法

5. **第五步**: 优化 Loaders（可选）
   - Loaders 是 DataManager 的内部组件，可以保留当前实现
   - 或者：接收 `DataManager` 而不是 `db`，通过 `data_mgr.db` 访问

---

## 6. 详细使用情况

### 6.1 BaseStrategy 中的 db 使用
```python
# 表注册和创建（已迁移）
self.data_mgr.db.register_table(...)  # ✅ 已迁移（通过 DataManager 访问）
self.data_mgr.db.create_registered_tables()  # ✅ 已迁移
self.data_mgr.db.registered_tables  # ✅ 已迁移
self.data_mgr.db.tables  # ✅ 已迁移

# 数据访问（已迁移到 DataManager）
self.data_mgr.get_model("stock_kline")  # ✅ 已迁移
```

### 6.2 LabelerService 中的 db 使用
```python
# 直接 SQL 查询（已迁移）
self.data_mgr.db.execute_query(sql, params)  # ✅ 已迁移（通过 DataManager 访问）

# 数据访问（已使用 data_mgr）
self.data_mgr.load_stock_list(...)  # ✅ 已迁移
self.data_mgr.load_klines(...)     # ✅ 已迁移
```

### 6.3 BFF API 中的 db_manager 使用
```python
# 初始化（已迁移）
self.data_mgr = DataManager()  # ✅ 已迁移（使用单例）

# 数据访问（已使用 DataManager）
self.data_mgr.get_model(...)  # ✅ 已迁移
```

---

## 7. 可行性评估

### ✅ 完全可以用 DataManager 替换（已完成）:
- `bff/api.py` - BFFApi ✅ **已完成迁移**
- `bff/APIs/stock_api.py` - StockApi ✅ **已完成迁移**
- `bff/APIs/investment_api.py` - InvestmentApi ✅ **已完成迁移**
- `app/analyzer/analyzer.py` - Analyzer ✅ **已完成迁移**
- `app/labeler/labeler.py` - LabelerService ✅ **已完成迁移**
- `app/analyzer/components/base_strategy.py` - BaseStrategy ✅ **已完成迁移**
  - 数据访问：✅ 使用 DataManager
  - 表管理：✅ 通过 `data_mgr.db` 访问

### ✅ 合理的直接使用（无需修改）:
- `app/data_manager/data_manager.py` - DataManager
- `app/data_manager/base_tables/*/model.py` - Models
- `app/data_manager/loaders/*.py` - Loaders (内部组件)

