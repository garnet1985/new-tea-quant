# Loaders 模块说明

## 📋 状态

**⚠️ 正在使用中，但建议逐步迁移到 DataService 架构**

这些 Loaders 目前仍在 `DataManager` 中被大量使用，包括：

- `KlineLoader`: K线数据加载
- `LabelLoader`: 标签数据加载  
- `MacroEconomyLoader`: 宏观经济数据加载
- `CorporateFinanceLoader`: 企业财务数据加载

## 🔄 迁移计划

新的架构方向是使用 `DataService`（位于 `app/data_manager/data_services/`），它提供了更清晰的业务领域划分和更好的封装。

### 当前使用情况

1. **DataManager 内部使用**：
   - `prepare_data()` 方法中委托给各个 Loaders
   - `load_klines()`, `load_macro_data()`, `load_corporate_finance_data()` 等方法
   - 标签相关的所有方法

2. **外部直接使用**：
   - `app/analyzer/strategy/RTB/feature_identity/reversal_identify.py` 中直接使用 `KlineLoader`

### 迁移建议

- ✅ **新代码**：优先使用 `DataService` 接口
- ⚠️ **旧代码**：保持使用 Loaders（向后兼容）
- 🔄 **逐步迁移**：将旧代码逐步迁移到 DataService

## 📝 文件列表

- `kline_loader.py` - K线数据加载器
- `label_loader.py` - 标签数据加载器
- `macro_loader.py` - 宏观经济数据加载器
- `corporate_finance_loader.py` - 企业财务数据加载器

## ⚠️ 注意

**不要删除这些文件**，它们仍在被使用。如果未来完全迁移到 DataService 架构，可以考虑：
1. 标记为 `@deprecated`
2. 添加迁移指南
3. 在完全迁移后再删除

