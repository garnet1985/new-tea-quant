# Indicator API 文档

**版本：** `0.3.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Indicator`；类型从 [`contracts.py`](./contracts.py) 导入。策略侧指标配置表见 [AVAILABLE_INDICATORS.md](./AVAILABLE_INDICATORS.md)。

---

## Indicator

**描述：** 技术指标计算门面（静态 API，勿实例化；代理 pandas-ta-classic）

#### calculate

`Indicator.calculate(indicator_name: str, klines: list[dict], **params) -> list[float] | dict[str, list[float]] | None`

- **类型：** `classmethod`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 通用入口；单列返回 list，多列返回 dict；失败返回 None

#### compute / compute_batch

`Indicator.compute(name, klines, **params)`  
`Indicator.compute_batch(klines, indicators_cfg) -> list[BatchIndicatorResult]`

- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 策略配置友好的计算与批量计算（共享 K 线上下文）

#### 便捷方法

`ma` / `ema` / `rsi` / `macd` / `bbands` / `atr` / `stoch` / `adx` / `obv`

- **状态：** `beta`
- **描述：** 常用指标快捷封装

#### list_indicators / get_indicator_help / warmup

- **状态：** `beta`
- **描述：** 列举库内指标、帮助文本、预热 TA 库导入
