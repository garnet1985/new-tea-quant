# Data Cursor 设计说明

**版本：** `0.2.0`

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## 构造路径

1. **`DataCursor(contracts=..., time_field_overrides=...)`**  
   对每个 **`source -> DataContract`**：读 **`contract.data`**；若 **`None`** 则 **`ValueError`**。  
   **时间字段**：优先 **`time_field_overrides[source]`**；否则 **`_resolve_time_field(contract)`**：
   - **`meta.attrs.type == NON_TIME_SERIES`** →非时序（内部用 **空字符串** 表示，**`until` 时整表输出**）。
   - 否则用 **`meta.attrs.time_axis_field`**，缺省为 **`"date"`**。

2. **`DataCursor.from_rows(rows_by_source, time_field_overrides=...)`**  
   无 **`DataContract`**；每源默认时间字段 **`"date"`**（可被 overrides 覆盖）。用于 Strategy 等已有 **行字典列表** 的结构。

---

## `until(as_of)`

- **`as_of`** 经 **`DateUtils.normalize(..., FMT_YYYYMMDD)`**；非法则 **`ValueError`**。
- **时序源**：从下标 **`cursor+1`** 起扫描 **`rows`**，若 **`time_field`** 值规范化后 **`<= as_of`** 则 **append到 `acc`** 并推进游标；遇 **大于 as_of** 则 **停止**（该源本次不再读后续行）。**`out[source] = acc`**（累计，非仅增量）。
- **非时序源**：**`out[source] = list(state.rows)`**，不推进切片逻辑。

多次调用 **`until`** 时，**`acc` 与 `cursor` 持续累积**；需重来则 **`reset()`**。

---

## `reset()`

各源 **`cursor = -1`**，**`acc = []`**。

---

## 与业务模块的衔接

- **`StrategyWorkerDataManager.rebuild_data_cursor`**、**`TagWorkerDataManager.rebuild_data_cursor`** 在 **contract 就绪** 后构建 **`DataCursorManager`** / **`DataCursor`**，并在按日循环中调用 **`until(as_of_date)`**。

---

## 相关文档

- [API.md](API.md)
