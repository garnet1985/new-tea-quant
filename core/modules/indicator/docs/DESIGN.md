# Indicator 设计说明

**版本：** `0.2.0`

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## K 线字段

**`calculate`** 使用的 **`_klines_to_dataframe`** 要求存在列：**`open`**、**`high`**、**`low`**、**`close`**。可选 **`volume`**。

调用方传入的价格字段含义由上游决定（例如 DataManager 的前复权 / 未复权 K 线）；本模块不做复权。

---

## `compute` 分层

策略配置路径优先走 **`compute` / `compute_batch`**：

1. **close 序列**：`rsi` 与 `_CLOSE_SERIES_INDICATORS`（如 `sma` / `ema`）
2. **裁剪 OHLCV**：便捷方法与 `_OHLCV_DIRECT_INDICATORS`（去掉无关列）
3. **宽表 `calculate`**：其余未知指标名回退完整行 → DataFrame

**`calculate`** 始终走完整 OHLCV 宽表，适合通用 / 探索调用。

---

## `calculate` 调用约定

对 **`cls._ta`** 上 **`indicator_name`** 指到的可调用对象，传入关键字参数：

- **`high` / `low` / `close` / `open_`**：来自 DataFrame（**`open_`** 因 pandas-ta 参数名）。
- **`volume`**：`df.get('volume')`，可能为 `None`。
- 其余 **`**params`** 原样透传（如 **`length`**、**`fast`**）。

若库函数签名与上述不兼容，需在业务侧换用其它指标名或自行封装。

---

## RSI 特例

**`rsi`** 不经过完整 OHLC DataFrame 管线：仅用 **`close`** 序列构造 **`pd.Series`** 再调 **`_ta.rsi`**，便于仅有收盘价的数据源。

---

## 返回值

- **单列**：`List[float]`（含前导 `NaN` 与库一致，调用方按需截断）。
- **多列**：`Dict[str, List[float]]`，键名为 pandas-ta 生成的列名（如 MACD、布林带）。

---

## 策略配置对齐

**[AVAILABLE_INDICATORS.md](./AVAILABLE_INDICATORS.md)** 描述 **`settings.data.indicators`** 中指标名与 **`compute(..., **params)`** 的对应关系；新增便捷方法时在 **`core/indicator.py`** 增加 **`@classmethod`** 包装即可。

---

## pandas-ta `verify_series` monkeypatch

加载 TA 库时，**`_patch_pandas_ta_verify_series`** 会替换 `pandas_ta_classic.utils._core.verify_series`：

- 数据行数不足时不再刷屏式英文告警，改为本模块 **DEBUG** 中文日志并返回 `None`。
- 补丁带 `_tea_patched` 标记，进程内只打一次。
- **不改变**「不足长度则跳过计算」的语义，只收口日志噪音。

---

## 相关文档

- [API.md](../API.md)

---

## 设计决策（原 DECISIONS.md）

# Indicator 设计决策

**版本：** `0.2.0`

---

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）