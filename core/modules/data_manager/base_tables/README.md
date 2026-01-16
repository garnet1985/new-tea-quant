# Base Tables Schemas

## 📋 概述

这个目录包含所有**基础表（Base Tables）**的 schema 定义。

基础表是系统运行所必需的核心数据表，与业务逻辑紧密相关，由 `DataManager` 统一管理。

## 📁 目录结构

```
base_tables/
├── stock_kline/            # K线数据表
│   └── schema.json
├── stock_list/             # 股票列表表
│   └── schema.json
├── gdp/                    # GDP数据表
│   └── schema.json
├── lpr/                    # LPR利率表
│   └── schema.json
├── shibor/                 # Shibor利率表
│   └── schema.json
├── corporate_finance/      # 企业财务表
│   └── schema.json
├── price_indexes/          # 价格指数表
│   └── schema.json
│   └── schema.json
├── stock_index_indicator/  # 股指指标表
│   └── schema.json
├── stock_index_indicator_weight/  # 股指权重表
│   └── schema.json
├── adj_factor/             # 复权因子表
│   └── schema.json
├── system_cache/           # 系统缓存表
│   └── schema.json
├── investment_trades/      # 投资交易表
│   └── schema.json
├── investment_operations/  # 投资操作表
│   └── schema.json
└── README.md              # 本文档
```

## 🎯 设计原则

### 基础表 vs 自定义表

项目中的数据表分为两类：

#### 1. 基础表（Base Tables）
**定义**：系统运行必需的核心数据表

**特点**：
- ✅ 表名直接使用 schema 中定义的名称（无前缀）
- ✅ Schema 定义在 `app/core_modules/data_manager/base_tables/`
- ✅ 由 `DataManager` 统一管理和创建
- ✅ 在系统初始化时自动创建

**示例**：
```
stock_kline
stock_list
gdp
lpr
...
```

#### 2. 自定义表（Custom Tables）
**定义**：策略或其他模块自定义的数据表

**特点**：
- ⚠️ 表名需要添加前缀（默认 `cust_`，策略可用 `策略key_`）
- ⚠️ Schema 定义在各自模块内
- ⚠️ 由各模块自行管理
- ⚠️ 目前暂未实现（待需求明确后实现）

**示例**（规划中）：
```
rtb_opportunities      # RTB策略的机会表
momentum_signals       # Momentum策略的信号表
cust_my_analysis       # 用户自定义分析表
```

## 📝 Schema 格式

每个表的 `schema.json` 定义表结构：

```json
{
    "name": "stock_kline",
    "primaryKey": ["id", "term", "date"],
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": true,
            "description": "股票代码"
        },
        {
            "name": "close",
            "type": "float",
            "isRequired": true,
            "description": "收盘价"
        }
    ],
    "indexes": [
        {
            "name": "idx_id_date",
            "fields": ["id", "date"],
            "unique": false
        }
    ]
}
```

**字段说明**：
- `name`: 表名
- `primaryKey`: 主键字段（可以是单个字段或字段数组）
- `fields`: 字段定义列表
  - `name`: 字段名
  - `type`: 数据类型（varchar, int, float, datetime 等）
  - `length`: 字段长度（varchar 类型必需）
  - `isRequired`: 是否必填
  - `description`: 字段描述
- `indexes`: 索引定义列表（可选）
  - `name`: 索引名
  - `fields`: 索引字段列表
  - `unique`: 是否唯一索引

## 🚀 使用方式

### 自动创建表

基础表由 `DatabaseManager` 在初始化时自动创建：

```python
from core.infra.db import DatabaseManager

# 初始化时会自动创建所有基础表
db = DatabaseManager()
db.initialize()  # 自动读取 base_tables/ 下的所有 schema.json 并创建表
```

### 添加新的基础表

1. 在 `base_tables/` 下创建新目录（如 `my_table/`）
2. 创建 `schema.json` 文件
3. 定义表结构
4. 重新初始化 DatabaseManager

示例：

```bash
# 创建新表目录
mkdir -p app/core_modules/data_manager/base_tables/my_table

# 创建 schema.json
cat > app/core_modules/data_manager/base_tables/my_table/schema.json << 'EOF'
{
    "name": "my_table",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "int",
            "isRequired": true,
            "description": "主键ID"
        },
        {
            "name": "data",
            "type": "varchar",
            "length": 255,
            "isRequired": false,
            "description": "数据"
        }
    ]
}
EOF
```

### 通过 DataManager 访问

基础表的数据访问通过 `DataManager` 及其子 Loader：

```python
from app.core.modules.data_manager import DataManager

data_mgr = DataManager(db=db)

# K线数据
klines = data_mgr.kline_loader.load_kline('000001.SZ', '20200101', '20241231')

# 宏观数据
macro_data = loader.macro_loader.load_gdp('2020Q1', '2024Q4')

# 企业财务
finance_data = loader.corporate_finance_loader.load_all('000001.SZ')
```

## ⚠️ 注意事项

1. **不要直接修改生产环境的 schema**
   - Schema 变更会影响现有数据
   - 需要做好数据迁移

2. **字段命名规范**
   - 使用小写和下划线（snake_case）
   - 避免使用 SQL 关键字
   - 使用有意义的英文名称

3. **主键设计**
   - 优先使用业务主键
   - 复合主键顺序很重要（影响索引效率）

4. **索引设计**
   - 为常用查询条件创建索引
   - 避免过多索引（影响写入性能）
   - 复合索引考虑字段顺序

## 📚 相关文档

- [DatabaseManager 文档](../../utils/db/README.md)
- [DataManager 文档](../README.md)
- [Schema 管理器文档](../../utils/db/schema_manager.py)

## 📅 更新日志

- **2024-12-04**: 从 `utils/db/tables/` 迁移到此目录
  - 实现职责分离（业务层 vs 基础设施层）
  - 统一由 DataManager 管理
  - 删除了 model.py（迁移到各 Loader）

