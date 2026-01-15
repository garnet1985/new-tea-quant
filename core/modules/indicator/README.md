# Indicator Module

**技术指标计算模块（通用模块）**

## 📋 概述

提供技术指标计算服务，基于 `pandas-ta-classic`，支持 150+ 技术指标。

**设计特点**:
- ✅ 通用模块：所有模块（strategy, tag, analyzer 等）都可使用
- ✅ Proxy 模式：代理 pandas-ta-classic，不搬运代码
- ✅ 便捷 API：8 个常用指标的快速调用方法
- ✅ 通用 API：支持所有 150+ 指标
- ✅ 静态工具类：无需实例化

---

## 🚀 快速开始

### 安装依赖

```bash
pip install pandas-ta-classic
```

### 基本使用

```python
from app.core.modules.indicator import IndicatorService

# 准备 K 线数据
klines = [
    {'date': '20251201', 'open': 10.0, 'high': 10.5, 'low': 9.8, 'close': 10.2, 'volume': 1000},
    {'date': '20251202', 'open': 10.2, 'high': 10.8, 'low': 10.0, 'close': 10.6, 'volume': 1200},
    # ... 更多数据
]

# 方式1: 便捷 API（推荐）
ma20 = IndicatorService.ma(klines, length=20)
rsi14 = IndicatorService.rsi(klines, length=14)
macd = IndicatorService.macd(klines)

# 方式2: 通用 API（支持所有指标）
cci = IndicatorService.calculate('cci', klines, length=20)
```

---

## 📚 API 文档

### 便捷 API（常用指标）

| 方法 | 说明 | 示例 |
|------|------|------|
| `ma(klines, length)` | 简单移动平均 | `ma20 = IndicatorService.ma(klines, 20)` |
| `ema(klines, length)` | 指数移动平均 | `ema12 = IndicatorService.ema(klines, 12)` |
| `rsi(klines, length)` | 相对强弱指标 | `rsi = IndicatorService.rsi(klines, 14)` |
| `macd(klines, fast, slow, signal)` | MACD | `macd = IndicatorService.macd(klines)` |
| `bbands(klines, length, std)` | 布林带 | `bb = IndicatorService.bbands(klines, 20)` |
| `atr(klines, length)` | 真实波动幅度 | `atr = IndicatorService.atr(klines, 14)` |
| `stoch(klines, k, d, smooth_k)` | 随机指标 | `kdj = IndicatorService.stoch(klines)` |
| `adx(klines, length)` | 平均趋向指数 | `adx = IndicatorService.adx(klines, 14)` |
| `obv(klines)` | 能量潮 | `obv = IndicatorService.obv(klines)` |

### 通用 API（所有指标）

```python
result = IndicatorService.calculate(indicator_name, klines, **params)
```

**支持的指标**（150+）:
- 趋势指标：SMA, EMA, WMA, DEMA, TEMA, etc.
- 动量指标：RSI, MACD, CCI, CMO, ROC, etc.
- 波动指标：ATR, BBANDS, NATR, etc.
- 成交量指标：OBV, AD, ADOSC, etc.
- 更多...

### 工具方法

```python
# 列出所有可用指标
all_indicators = IndicatorService.list_indicators()

# 查看指标帮助
help_text = IndicatorService.get_indicator_help('macd')
```

---

## 📊 数据格式

### 输入格式

```python
klines = [
    {
        'date': '20251219',
        'open': 10.0,
        'high': 10.5,
        'low': 9.8,
        'close': 10.2,
        'volume': 1000
    },
    # ... 更多数据
]
```

**必需字段**: `open`, `high`, `low`, `close`  
**可选字段**: `volume`, `date`

### 输出格式

**单列指标**（MA, RSI, ATR 等）:
```python
[10.1, 10.2, 10.3, ...]  # List[float]
```

**多列指标**（MACD, BBANDS 等）:
```python
{
    'MACD_12_26_9': [...],
    'MACDs_12_26_9': [...],
    'MACDh_12_26_9': [...]
}  # Dict[str, List[float]]
```

---

## 💡 使用场景

### 1. 在 Strategy 模块中使用

```python
class MyStrategyWorker(BaseStrategyWorker):
    def scan_opportunity(self):
        from app.core.modules.indicator import IndicatorService
        
        klines = self.data_manager.get_klines()
        
        # 计算指标
        ma20 = IndicatorService.ma(klines, 20)
        rsi = IndicatorService.rsi(klines, 14)
        
        # 策略逻辑
        if klines[-1]['close'] > ma20[-1] and rsi[-1] < 30:
            return Opportunity(...)
```

### 2. 在 Tag 模块中使用

```python
class MyTagWorker(BaseTagWorker):
    def calculate_tag(self):
        from app.core.modules.indicator import IndicatorService
        
        klines = self.data_manager.get_klines()
        
        # 计算技术指标
        rsi = IndicatorService.rsi(klines, 14)
        
        return {
            'rsi_oversold': rsi[-1] < 30,
            'rsi_value': rsi[-1]
        }
```

### 3. 在 Analyzer 模块中使用

```python
from app.core.modules.indicator import IndicatorService

# 分析历史数据
def analyze_stock_trend(stock_id):
    klines = load_klines(stock_id)
    
    ma20 = IndicatorService.ma(klines, 20)
    ma60 = IndicatorService.ma(klines, 60)
    
    # 分析趋势
    if ma20[-1] > ma60[-1]:
        return "上升趋势"
```

---

## ⚙️ 技术栈

- **底层库**: `pandas-ta-classic` 0.3.59
- **依赖**: `pandas >= 2.0.0`, `numpy >= 2.0.0`

---

## 📝 注意事项

1. **数据长度要求**
   - 大多数指标需要足够的历史数据
   - 建议至少 60 条 K 线数据
   - MACD 等指标至少需要 26+ 条数据

2. **返回值处理**
   - 数据不足时返回 `None`
   - 计算失败时返回 `None`
   - 使用前检查返回值

3. **性能考虑**
   - 单个指标计算：< 10ms（1000 条 K 线）
   - 不缓存计算结果（按需计算）
   - 未来可优化为 Worker 级别缓存

---

## 🔧 开发

### 运行测试

```bash
cd /Users/garnet/Desktop/stocks-py
python3 app/core/modules/indicator/indicator_service.py
```

### 添加新的便捷 API

在 `indicator_service.py` 中添加新方法：

```python
@classmethod
def your_indicator(cls, klines, **params):
    """你的指标说明"""
    return cls.calculate('your_indicator_name', klines, **params)
```

---

## 📚 相关文档

- [Strategy 系统设计文档](../strategy/docs/DESIGN.md)
- [pandas-ta-classic 文档](https://github.com/xgboosted/pandas-ta-classic)

---

**作者**: Strategy Team  
**日期**: 2025-12-19  
**版本**: 1.0
