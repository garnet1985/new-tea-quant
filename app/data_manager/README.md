# DataManager - 全局数据管理服务

## 📦 架构设计

```
app/data_manager/
├── data_manager.py              # 主入口
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
- **DataManager**: 主入口，统一API
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
from app.data_manager import DataManager

data_mgr = DataManager(db=db)

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

#### 场景1：子进程只取数据（简单场景）

```python
from concurrent.futures import ProcessPoolExecutor

# 使用静态方法（每次创建新连接）
with ProcessPoolExecutor() as executor:
    futures = [
        executor.submit(
            DataManager.load_klines_in_child,
            stock_id, 'daily', 'qfq', {'is_verbose': False}
        )
        for stock_id in stock_list
    ]
    results = [f.result() for f in futures]
```

**适用场景**：子进程只负责取数据，取完就结束

---

#### 场景2：子进程做复杂任务（推荐，回测场景）

```python
from concurrent.futures import ProcessPoolExecutor

def simulate_stock(stock_id, db_config, strategy_params):
    """在子进程中模拟一个股票的交易"""
    
    # ✅ 在子进程开始时创建一次loader
    data_mgr = DataManager.create_for_child_process(db_config)
    
    # 加载数据（复用连接，多次调用）
    klines = loader.load_daily_qfq(stock_id)
    macro_data = loader.load_gdp_data(...)
    
    # 执行策略回测（很多步骤）
    strategy = Strategy(strategy_params)
    for date in trading_dates:
        signal = strategy.generate_signal(klines, date)
        # ... 执行交易模拟
    
    return portfolio.get_performance()

# 主进程
with ProcessPoolExecutor(max_workers=8) as executor:
    futures = [
        executor.submit(simulate_stock, stock_id, db_config, strategy_params)
        for stock_id in stock_list
    ]
    results = [f.result() for f in futures]
```

**适用场景**：子进程需要执行复杂任务（如回测），数据加载只是其中一步

**关键差异**：
- 场景1：每次调用都创建新连接（开销大）
- 场景2：创建一次，复用连接（性能好）✅

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
| `create_for_child_process(db_config)` | 创建进程安全的DataManager实例 |
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
5. **独立性强**：DataManager不依赖DataSourceService
