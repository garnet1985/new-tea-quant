# Indicator 模块概览

> **提示**：本文档提供 Indicator 模块的快速上手视图。  
> 详细的设计理念、架构设计和决策记录请参考同目录下的 `architecture.md` 和 `decisions.md`。

## 📋 模块简介

`Indicator` 模块是系统的**技术指标计算模块**，基于第三方库 `pandas-ta-classic`，为策略、标签、分析等模块提供统一的指标计算服务。

**核心特性**：

- **通用模块**：`strategy`、`tag`、`analyzer` 等任意模块都可以使用
- **Proxy 模式**：不搬运具体指标实现，而是代理 `pandas-ta-classic` 的 API
- **双层 API**：
  - 便捷 API：为常用 8～10 个指标提供友好方法（如 `ma`、`rsi`、`macd`）
  - 通用 API：`calculate(name, klines, **params)` 支持所有 150+ 指标
- **静态工具类**：`IndicatorService` 设计为类方法 / 静态方法，无需实例化

> 详细的架构设计请参考 [architecture.md](./architecture.md)

---

## 📁 模块的文件夹结构

```text
core/modules/indicator/
├── __init__.py            # 导出 IndicatorService
├── indicator_service.py   # IndicatorService 核心实现
└── README.md              # 使用说明（面向开发者）
```

---

## 🚀 模块的使用方法

### 基本使用（策略 / 标签 / 分析模块通用）

```python
from core.modules.indicator import IndicatorService

# 准备 K 线数据（List[Dict] 格式）
klines = [
    {"date": "20251201", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000},
    {"date": "20251202", "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.6, "volume": 1200},
    # ...
]

# 方式 1：便捷 API（推荐，用于常用指标）
ma20 = IndicatorService.ma(klines, length=20)
rsi14 = IndicatorService.rsi(klines, length=14)
macd = IndicatorService.macd(klines)

# 方式 2：通用 API（支持所有 pandas-ta 指标）
cci = IndicatorService.calculate("cci", klines, length=20)
```

### 在 Strategy 模块中使用示例

```python
def scan_opportunity(self):
    from core.modules.indicator import IndicatorService

    klines = self.data_manager.stock.kline.load(self.stock_id, term="daily")
    ma20 = IndicatorService.ma(klines, 20)
    rsi = IndicatorService.rsi(klines, 14)

    # 简单例子：收盘价上穿 MA20 且 RSI 超卖
    if klines[-1]["close"] > ma20[-1] and rsi[-1] < 30:
        ...
```

---

## 📊 数据格式约定（概览）

- **输入格式（K 线）**：`List[Dict]`
  - 必需字段：`open`, `high`, `low`, `close`
  - 可选字段：`volume`, `date`

- **输出格式**：
  - 单列指标（如 MA / RSI / ATR）：`List[float]`
  - 多列指标（如 MACD / BBANDS）：`Dict[str, List[float]]`

> 更详细的数据格式与边界行为说明见 `architecture.md`。

---

## 📚 模块详细文档

- **[architecture.md](./architecture.md)**：架构文档，包含 Proxy 设计、数据流与 API 设计
- **[decisions.md](./decisions.md)**：重要决策记录，例如「为何复用 pandas-ta」与「为何采用静态工具类」

> **阅读建议**：先阅读本文档快速上手，再阅读 `architecture.md` 理解内部设计，最后阅读 `decisions.md` 了解设计取舍。 
