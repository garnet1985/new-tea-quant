# Available Indicators

本文件用于说明策略 `settings.data.indicators` 可用指标与推荐写法。

## 命名原则

- 指标名直接使用 `pandas-ta-classic` 原生函数名（例如 `sma`、`rsi`、`macd`）。
- 参数直接透传给 `IndicatorService.calculate(name, klines, **params)`。
- 优先使用 `length` 参数名（与 ta-classic 一致）；不再推荐 `period`。

## 高频常用指标（推荐优先使用）

下面是更适合大多数策略作者的高频指标（约 20 个），建议先从这些开始。

| 指标名 | 典型参数 | 返回形态 | 说明 |
|---|---|---|---|
| `sma` | `length` | `List[float]` | 简单移动平均 |
| `ema` | `length` | `List[float]` | 指数移动平均 |
| `wma` | `length` | `List[float]` | 加权移动平均 |
| `vwma` | `length` | `List[float]` | 成交量加权均线 |
| `hma` | `length` | `List[float]` | Hull 均线 |
| `rsi` | `length` | `List[float]` | 相对强弱指标 |
| `macd` | `fast, slow, signal` | `Dict[str, List[float]]` | MACD 三列 |
| `stoch` | `k, d, smooth_k` | `Dict[str, List[float]]` | 随机指标（K/D） |
| `cci` | `length` | `List[float]` | 顺势指标 |
| `roc` | `length` | `List[float]` | 变动率 |
| `willr` | `length` | `List[float]` | 威廉指标 |
| `mfi` | `length` | `List[float]` | 资金流量指数 |
| `bbands` | `length, std` | `Dict[str, List[float]]` | 布林带 |
| `atr` | `length` | `List[float]` | 平均真实波动 |
| `adx` | `length` | `List[float]` | 趋势强度 |
| `supertrend` | `length, multiplier` | `Dict[str, List[float]]` | 超级趋势 |
| `psar` | `af0, af, max_af` | `Dict[str, List[float]]` | 抛物线转向 |
| `obv` | 无（或默认） | `List[float]` | 能量潮 |
| `ad` | 无（或默认） | `List[float]` | 累积/派发线 |
| `adosc` | `fast, slow` | `List[float]` | Chaikin 振荡器 |
| `cmf` | `length` | `List[float]` | Chaikin 资金流量 |

## 其他可扩展指标（同格式速查）

这部分用于展示支持广度，使用频率通常低于上面的高频列表。

| 指标名 | 典型参数 | 返回形态 | 说明 |
|---|---|---|---|
| `rma` | `length` | `List[float]` | Wilder 平滑均线 |
| `zlma` | `length` | `List[float]` | 零滞后均线 |
| `stochrsi` | `length, rsi_length, k, d` | `Dict[str, List[float]]` | RSI 上的随机指标 |
| `mom` | `length` | `List[float]` | 动量 |
| `cmo` | `length` | `List[float]` | 钱德动量摆动 |
| `uo` | `fast, medium, slow` | `List[float]` | 终极振荡器 |
| `ppo` | `fast, slow, signal` | `Dict[str, List[float]]` | 百分比价格振荡 |
| `trix` | `length, signal` | `Dict[str, List[float]]` | 三重指数平滑动量 |
| `kst` | `roc1, roc2, roc3, roc4` | `Dict[str, List[float]]` | KST 动量组合 |
| `kc` | `length, scalar` | `Dict[str, List[float]]` | Keltner 通道 |
| `donchian` | `lower_length, upper_length` | `Dict[str, List[float]]` | 唐奇安通道 |
| `natr` | `length` | `List[float]` | 标准化 ATR |
| `true_range` | 无（或默认） | `List[float]` | 真实波动范围 |
| `aroon` | `length` | `Dict[str, List[float]]` | 趋势方向强度 |
| `vortex` | `length` | `Dict[str, List[float]]` | 漩涡指标 |
| `efi` | `length` | `List[float]` | Elder Force Index |
| `pvt` | 无（或默认） | `List[float]` | 价量趋势 |
| `eom` | `length` | `List[float]` | Ease of Movement |

## 配置示例

```python
"indicators": {
    # 趋势
    "sma": [{"length": 5}, {"length": 20}, {"length": 60}],
    "ema": [{"length": 12}, {"length": 26}],
    "supertrend": [{"length": 10, "multiplier": 3.0}],

    # 动量
    "rsi": [{"length": 14}],
    "macd": [{"fast": 12, "slow": 26, "signal": 9}],
    "stoch": [{"k": 14, "d": 3, "smooth_k": 3}],

    # 波动/量能
    "bbands": [{"length": 20, "std": 2.0}],
    "atr": [{"length": 14}],
    "obv": [{}],
    "mfi": [{"length": 14}],
}
```

## 全量指标清单（自动导出）

`IndicatorService` 会直接代理 `pandas-ta-classic`，理论上可用其公开函数全集。建议在安装依赖后执行以下命令导出当前环境的完整清单：

```bash
python3 - <<'PY'
from core.modules.indicator import IndicatorService
for name in IndicatorService.list_indicators():
    print(name)
PY
```

如需保存到文件：

```bash
python3 - <<'PY' > indicator_names.txt
from core.modules.indicator import IndicatorService
for name in IndicatorService.list_indicators():
    print(name)
PY
```

> 注意：本仓库运行环境若未安装 `pandas-ta-classic`，上述命令会报 `ImportError`，先执行 `pip install pandas-ta-classic`。
