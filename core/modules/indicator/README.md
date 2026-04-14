# Indicator 模块（`modules.indicator`）

**`IndicatorService`** 是 **`pandas-ta-classic`** 的薄代理：将 **`List[Dict]`** K 线转为 `DataFrame`，调用库内与 **`indicator_name`** 同名的函数，再把 **Series / DataFrame** 转回 **`List[float]`** 或 **`Dict[str, List[float]]`**。无实例状态、**不做缓存**；**`RSI`** 单独实现，仅需 **`close`** 列即可。

策略里 **`settings.data.indicators`** 的命名与参数约定见 **[AVAILABLE_INDICATORS.md](AVAILABLE_INDICATORS.md)**。

## 适用场景

- Strategy / Tag / 分析脚本中在内存里对 K 线序列算 MA、RSI、MACD 等。
- 通过 **`calculate('cci', klines, ...)`** 调用库内任意已实现指标（见 **`list_indicators()`**）。

## 快速开始

```bash
pip install pandas-ta-classic
```

```python
from core.modules.indicator import IndicatorService

klines = [
    {"date": "20251201", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000},
    # ... 足够长度]
ma = IndicatorService.ma(klines, length=20)
rsi = IndicatorService.rsi(klines, length=14)
```

## 目录结构

```text
core/modules/indicator/
├── module_info.yaml
├── README.md
├── AVAILABLE_INDICATORS.md   # 策略 indicators 配置与指标表
├── indicator_service.py
├── __init__.py
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 模块依赖（`module_info.yaml`）

运行时依赖 **`pandas`**、**`pandas-ta-classic`**（PyPI）；无其它 NTQ 模块硬依赖。

## 相关文档

- [架构与边界](docs/ARCHITECTURE.md)
- [数据列与 RSI 特例](docs/DESIGN.md)
- [公开 API](docs/API.md)
- [设计决策](docs/DECISIONS.md)
- [可用指标与配置表](AVAILABLE_INDICATORS.md)
