# DataLoader - 全局数据加载服务

## 📦 架构设计

```
app/data_loader/
├── data_loader.py              # 主入口（~150行）
├── loaders/
│   ├── __init__.py
│   └── kline_loader.py        # K线专用加载器（~280行）
└── helpers/
    ├── __init__.py
    ├── adjustment.py          # 复权计算工具（~140行）
    └── filtering.py           # 数据过滤工具（~40行）
```

## 🎯 设计原则

### 1. 按业务领域分层
- **DataLoader**: 主入口，统一API
- **KlineLoader**: K线数据专用加载器
- **Helpers**: 底层工具（复权、过滤）

### 2. 便捷方法优先
- **80%场景**: 快捷方法，零配置
- **20%场景**: 完整方法，全配置

### 3. 多进程友好
- 静态工厂方法：`create_for_child_process()`
- 静态加载方法：`load_klines_in_child()`

## 🚀 使用示例

### 快捷方法（80%场景）

```python
from app.data_loader import DataLoader

loader = DataLoader(db)

# 最常用：日线前复权
records = loader.load_daily_qfq('000001.SZ')

# DataFrame版本（分析用）
df = loader.load_daily_qfq_df('000001.SZ')

# 周线/月线
records = loader.load_weekly_qfq('000001.SZ')
records = loader.load_monthly_qfq('000001.SZ')

# 不复权（调试用）
records = loader.load_raw_klines('000001.SZ', 'daily')
```

### 完整方法（20%场景）

```python
# 需要灵活配置时
records = loader.load_klines(
    stock_id='000001.SZ',
    term='weekly',
    start_date='20200101',
    end_date='20231231',
    adjust='hfq',              # 后复权
    filter_negative=False,     # 保留负值
    as_dataframe=True          # 返回DataFrame
)
```

### 多进程支持

```python
from concurrent.futures import ProcessPoolExecutor

def process_stock(stock_id, db_config):
    # 在子进程中创建DataLoader
    loader = DataLoader.create_for_child_process(db_config)
    return loader.load_daily_qfq(stock_id)

# 或使用静态方法
with ProcessPoolExecutor() as executor:
    future = executor.submit(
        DataLoader.load_klines_in_child,
        '000001.SZ', 'daily', 'qfq', {'is_verbose': False}
    )
    result = future.result()
```

## 📚 API速查

### 快捷方法

| 方法 | 说明 | 返回类型 |
|-----|-----|---------|
| `load_daily_qfq(stock_id)` | 日线前复权 | List[Dict] |
| `load_weekly_qfq(stock_id)` | 周线前复权 | List[Dict] |
| `load_monthly_qfq(stock_id)` | 月线前复权 | List[Dict] |
| `load_daily_qfq_df(stock_id)` | 日线前复权（DataFrame） | DataFrame |
| `load_weekly_qfq_df(stock_id)` | 周线前复权（DataFrame） | DataFrame |
| `load_monthly_qfq_df(stock_id)` | 月线前复权（DataFrame） | DataFrame |
| `load_raw_klines(stock_id, term)` | 原始K线（不复权） | List[Dict] |
| `load_raw_klines_df(stock_id, term)` | 原始K线（DataFrame） | DataFrame |

### 完整方法

| 方法 | 说明 |
|-----|-----|
| `load_klines(stock_id, term, start_date, end_date, adjust, filter_negative, as_dataframe)` | 完整参数，支持所有配置 |

### 多进程支持

| 方法 | 说明 |
|-----|-----|
| `create_for_child_process(db_config)` | 创建进程安全的DataLoader实例 |
| `load_klines_in_child(stock_id, term, adjust, db_config, as_dataframe)` | 静态加载方法（进程安全） |

## 🔄 向后兼容

旧的analyzer代码仍然有效：

```python
# 旧方法（向后兼容）
kline_data = loader.load_stock_klines_data(stock_id, settings)
```

## ⚡ 性能特点

- **List版本**: 使用for循环复权（~0.1秒）
- **DataFrame版本**: 使用merge_asof复权（~0.12秒）
- **性能差异**: 仅1.1倍，用户无感知
- **选择建议**: 
  - 需要性能 → `as_dataframe=False`
  - 需要分析 → `as_dataframe=True`

## 🏗️ 架构优势

1. **职责清晰**：每个文件<300行
2. **易于测试**：可单独测试KlineLoader
3. **易于扩展**：新增loader不影响现有代码
4. **向后兼容**：旧代码无需修改
5. **独立性强**：DataLoader不依赖DataSourceService
