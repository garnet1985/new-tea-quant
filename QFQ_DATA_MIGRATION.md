# 数据复权方式迁移说明

## 修改概述

将股票K线数据从**不复权**改为**前复权（qfq）**，以提供更准确的历史低点分析。

## 修改内容

### 1. 数据获取方式变更

**修改前（不复权）：**
```python
# 使用 pro_api 接口，默认不复权
return self.api.daily(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
return self.api.weekly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
return self.api.monthly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
```

**修改后（前复权）：**
```python
# 使用 pro_bar 接口，指定前复权
import tushare as ts
return ts.pro_bar(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'], adj='qfq')
return ts.pro_bar(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'], adj='qfq', freq='W')
return ts.pro_bar(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'], adj='qfq', freq='M')
```

### 2. 修改的文件

- `stocks-py/app/data_source/providers/tushare/main.py`
  - 修改 `fetch_kline_data` 方法

## 为什么选择前复权？

### 1. 策略特点分析
历史低点策略需要：
- 准确的历史价格比较
- 连续的价格走势
- 公平的当前价格与历史低点对比

### 2. 前复权优势
- **价格连续性**：保持价格走势的连续性
- **历史低点准确性**：反映真实的投资机会
- **投资决策合理性**：当前价格与历史低点的比较更有意义

### 3. 复权方式对比
| 复权方式 | 适用场景 | 对策略的影响 |
|---------|---------|-------------|
| 不复权 | 原始数据分析 | 价格跳跃影响分析准确性 |
| 前复权 | 技术分析、策略回测 | ✅ 最适合历史低点策略 |
| 后复权 | 长期投资分析 | 可能掩盖短期机会 |

## 数据字段映射

`ts.pro_bar()` 返回的字段与现有代码完全兼容：

| pro_bar字段 | 数据库字段 | 说明 |
|------------|-----------|------|
| `trade_date` | `date` | 交易日期 |
| `open` | `open` | 开盘价 |
| `close` | `close` | 收盘价 |
| `high` | `highest` | 最高价 |
| `low` | `lowest` | 最低价 |
| `vol` | `volume` | 成交量 |
| `amount` | `amount` | 成交额 |
| `change` | `priceChangeDelta` | 价格变动 |
| `pct_chg` | `priceChangeRateDelta` | 价格变动率 |
| `pre_close` | `preClose` | 前日收盘价 |

## 测试验证

运行测试脚本验证数据获取：
```bash
python test_qfq_data.py
```

## 注意事项

1. **数据重新获取**：由于复权方式改变，建议重新获取历史数据
2. **策略回测**：使用新数据重新进行策略回测
3. **性能影响**：`pro_bar` 接口相比 `pro_api` 可能有不同的性能表现

## 预期效果

- 历史低点识别更准确
- 投资机会判断更合理
- 策略回测结果更可靠 