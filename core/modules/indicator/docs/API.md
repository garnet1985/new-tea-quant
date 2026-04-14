# Indicator 模块 API 文档

**版本：** `0.2.0`

本文档采用统一 API 条目格式。`IndicatorService` 为**仅类方法**的工具类，无实例化。

---

## IndicatorService

### 函数名
`calculate(cls, indicator_name: str, klines: List[Dict[str, Any]], **params) -> Union[List[float], Dict[str, List[float]], None]`

- 状态：`stable`
- 描述：通用入口：在 **`pandas_ta_classic`** 上取 **`indicator_name`** 同名函数，传入 OHLCV 与 **`**params`**。单列返回 **`List[float]`**，多列返回 **`Dict[str, List[float]]`**；不支持或失败返回 **`None`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `indicator_name` | `str` | 与库中可调用名一致，如 `sma`、`macd` |
| `klines` | `List[Dict[str, Any]]` | 须含 `open`/`high`/`low`/`close`，可选 `volume` |
| `**params` | `Any` | 传给 TA 函数的参数，如 `length=20` |

- 返回值：`List[float]`、`Dict[str, List[float]]` 或 `None`

---

### 函数名
`ma(cls, klines: List[Dict[str, Any]], length: int = 20) -> Optional[List[float]]`

- 状态：`stable`
- 描述：简单移动平均，等价 **`calculate('sma', klines, length=length)`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | K 线 |
| `length` (可选) | `int` | 周期，默认 `20` |

- 返回值：`Optional[List[float]]`

---

### 函数名
`ema(cls, klines: List[Dict[str, Any]], length: int = 20) -> Optional[List[float]]`

- 状态：`stable`
- 描述：指数移动平均，等价 **`calculate('ema', klines, length=length)`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | K 线 |
| `length` (可选) | `int` | 默认 `20` |

- 返回值：`Optional[List[float]]`

---

### 函数名
`rsi(cls, klines: List[Dict[str, Any]], length: int = 14) -> Optional[List[float]]`

- 状态：`stable`
- 描述：**仅用 `close`** 序列计算 RSI，不依赖完整 OHLC DataFrame 路径。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | 至少含 `close` |
| `length` (可选) | `int` | 默认 `14` |

- 返回值：`Optional[List[float]]`

---

### 函数名
`macd(cls, klines: List[Dict[str, Any]], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, List[float]]]`

- 状态：`stable`
- 描述：MACD 三列字典，键名由库生成（如 `MACD_12_26_9`）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | K 线 |
| `fast` (可选) | `int` | 默认 `12` |
| `slow` (可选) | `int` | 默认 `26` |
| `signal` (可选) | `int` | 默认 `9` |

- 返回值：`Optional[Dict[str, List[float]]]`

---

### 函数名
`bbands(cls, klines: List[Dict[str, Any]], length: int = 20, std: float = 2.0) -> Optional[Dict[str, List[float]]]`

- 状态：`stable`
- 描述：布林带三轨。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | K 线 |
| `length` (可选) | `int` | 默认 `20` |
| `std` (可选) | `float` | 默认 `2.0` |

- 返回值：`Optional[Dict[str, List[float]]]`

---

### 函数名
`atr(cls, klines: List[Dict[str, Any]], length: int = 14) -> Optional[List[float]]`

- 状态：`stable`
- 描述：真实波幅 ATR。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | K 线 |
| `length` (可选) | `int` | 默认 `14` |

- 返回值：`Optional[List[float]]`

---

### 函数名
`stoch(cls, klines: List[Dict[str, Any]], k: int = 14, d: int = 3, smooth_k: int = 3) -> Optional[Dict[str, List[float]]]`

- 状态：`stable`
- 描述：随机指标（K/D 等列）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | K 线 |
| `k` (可选) | `int` | 默认 `14` |
| `d` (可选) | `int` | 默认 `3` |
| `smooth_k` (可选) | `int` | 默认 `3` |

- 返回值：`Optional[Dict[str, List[float]]]`

---

### 函数名
`adx(cls, klines: List[Dict[str, Any]], length: int = 14) -> Optional[List[float]]`

- 状态：`stable`
- 描述：平均趋向指数。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | K 线 |
| `length` (可选) | `int` | 默认 `14` |

- 返回值：`Optional[List[float]]`

---

### 函数名
`obv(cls, klines: List[Dict[str, Any]]) -> Optional[List[float]]`

- 状态：`stable`
- 描述：能量潮 OBV。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `klines` | `List[Dict[str, Any]]` | K 线 |

- 返回值：`Optional[List[float]]`

---

### 函数名
`list_indicators(cls) -> List[str]`

- 状态：`stable`
- 描述：列出 **`pandas_ta_classic`** 上可调用、非下划线开头的名称（排序后）。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`List[str]`

---

### 函数名
`get_indicator_help(cls, indicator_name: str) -> str`

- 状态：`stable`
- 描述：返回该指标可调用对象的 **`__doc__`**，不存在则返回提示字符串。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `indicator_name` | `str` | 指标名 |

- 返回值：`str`

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
- [AVAILABLE_INDICATORS.md](../AVAILABLE_INDICATORS.md)
