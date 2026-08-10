# Indicator API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Indicator`；类型从 [`contracts.py`](./contracts.py) 导入。策略侧指标配置表见 [docs/AVAILABLE_INDICATORS.md](./docs/AVAILABLE_INDICATORS.md)。

---

## Indicator

**描述：** 技术指标计算门面（静态 API，勿实例化；代理 pandas-ta-classic）

### calculate

`Indicator.calculate(indicator_name: str, klines: list[dict], **params) -> list[float] | dict[str, list[float]] | None`

- **类型：** `classmethod`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 通用入口；单列返回 list，多列返回 dict；失败返回 `None`
- **参数：**
  - `indicator_name`：pandas-ta-classic 函数名（如 `sma`、`cci`）
  - `klines`：K 线 `list[dict]`（至少含 OHLC；部分指标需 `volume`）
  - `**params`：透传给 TA 库（如 `length`、`fast`）

### compute

`Indicator.compute(name: str, klines: list[dict], **params) -> list[float] | dict[str, list[float]] | None`

- **类型：** `classmethod`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 策略配置友好的单指标计算（close / 裁剪 OHLCV / 宽表分层）

### compute_batch

`Indicator.compute_batch(klines: list[dict], indicators_cfg: dict) -> list[BatchIndicatorResult]`

- **类型：** `classmethod`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 批量计算；共享 K 线上下文；每项为 `(name, params, values)`

### 便捷方法

| 方法 | 签名要点 | 返回 |
|------|----------|------|
| `ma` / `ema` | `(klines, length=20)` | `list[float] \| None` |
| `rsi` | `(klines, length=14)` | `list[float] \| None` |
| `macd` | `(klines, fast=12, slow=26, signal=9)` | `dict[str, list[float]] \| None` |
| `bbands` | `(klines, length=20, std=2)` | `dict[str, list[float]] \| None` |
| `atr` | `(klines, length=14)` | `list[float] \| None` |
| `stoch` | `(klines, k=14, d=3, smooth_k=3)` | `dict[str, list[float]] \| None` |
| `adx` | `(klines, length=14)` | `dict[str, list[float]] \| None` |
| `obv` | `(klines)` | `list[float] \| None` |

- **状态：** `beta`
- **描述：** 常用指标快捷封装（内部走 `compute` / TA 代理）

### list_indicators

`Indicator.list_indicators() -> list[str]`

- **状态：** `beta`
- **描述：** 列举当前环境 pandas-ta-classic 公开指标名

### get_indicator_help

`Indicator.get_indicator_help(indicator_name: str) -> str`

- **状态：** `beta`
- **描述：** 返回指标 docstring（或「无文档」）

### warmup

`Indicator.warmup() -> None`

- **状态：** `beta`
- **描述：** 预热 TA 库导入（进程内只加载一次）
