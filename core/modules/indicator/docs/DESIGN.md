# Indicator 设计说明

**版本：** `0.2.0`

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## K 线字段

**`calculate`** 使用的 **`_klines_to_dataframe`** 要求存在列：**`open`**、**`high`**、**`low`**、**`close`**。可选 **`volume`**。

兼容：若仅有 **`highest` / `lowest`**（无 `high` / `low`），会映射为 **`high` / `low`** 再校验。

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

**`AVAILABLE_INDICATORS.md`** 描述 **`settings.data.indicators`** 中 **`indicator_name`** 与 **`calculate(..., **params)`** 的对应关系；新增便捷方法时在 **`indicator_service.py`** 增加 **`@classmethod`** 包装即可。

---

## 相关文档

- [API.md](API.md)
