# Tables 目录（已废弃）

## ⚠️ 重要提示

**本目录已废弃，仅保留用于向后兼容！**

## 📅 迁移说明

### Schema 文件已迁移
- **旧位置**: `utils/db/tables/*/schema.json`
- **新位置**: `app/data_loader/base_tables/*/schema.json`
- **迁移时间**: 2024-12-04

### Model 文件计划废弃
- **当前状态**: 保留在此目录，但标记为 DEPRECATED
- **未来计划**: 迁移到各 Loader（KlineLoader, MacroLoader 等）
- **完成时间**: TBD

## 🎯 新架构

### 职责分离

#### 旧架构（已废弃）
```
utils/db/tables/stock_kline/    ← 业务数据定义在基础设施层 ❌
    ├── schema.json
    └── model.py
```

#### 新架构（推荐）
```
app/data_loader/base_tables/stock_kline/    ← 业务数据定义归业务层 ✅
    └── schema.json

app/data_loader/loaders/kline_loader.py     ← 数据访问逻辑
```

## 📚 新的使用方式

### 不要这样（旧代码）
```python
# ❌ 旧方式（废弃）
from utils.db.db_model import BaseTableModel
model = BaseTableModel('stock_kline', db)
records = model.load(condition="id = %s", params=('000001.SZ',))
```

### 应该这样（新代码）
```python
# ✅ 新方式（推荐）
from app.data_loader import DataLoader
loader = DataLoader(db)
records = loader.kline_loader.load_kline('000001.SZ', '20200101', '20241231')
```

## 🗂️ 目录内容说明

当前目录仍保留以下文件（仅用于向后兼容）：

| 文件 | 状态 | 说明 |
|------|------|------|
| `*/model.py` | ⚠️ 废弃中 | 将迁移到 DataLoader |
| `*/schema.json` | ✅ 已迁移 | 已移至 `app/data_loader/base_tables/` |

## 🔗 相关文档

- [新的 Base Tables 文档](../../../app/data_loader/base_tables/README.md)
- [DatabaseManager 文档](../README.md)
- [DataLoader 文档](../../../app/data_loader/README.md)

## ⏰ 迁移时间线

- ✅ **2024-12-04**: Schema 文件迁移完成
- 🔜 **待定**: Model 文件开始迁移
- 🔜 **待定**: 本目录完全删除

## 💡 如需帮助

如有疑问，请参考：
- [重构总结文档](../REFACTOR_SUMMARY.md)
- [清理总结文档](../CLEANUP_SUMMARY.md)
