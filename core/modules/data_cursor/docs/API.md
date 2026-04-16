# Data Cursor 模块 API 文档

**版本：** `0.2.0`

本文档采用统一 API 条目格式。内部 **`_CursorState`** 不对外。

---

## DataCursor

### 函数名
`DataCursor(contracts: Mapping[Hashable, DataContract], time_field_overrides: Optional[Mapping[Hashable, Optional[str]]] = None) -> DataCursor`

- 状态：`stable`
- 描述：数据类构造；**`__post_init__`** 为每个 **`contract`** 建 **`_CursorState`**，要求 **`contract.data` 非空**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `contracts` | `Mapping[Hashable, DataContract]` | 数据源键 → 已加载的契约 |
| `time_field_overrides` (可选) | `Optional[Mapping[Hashable, Optional[str]]]` | 每源时间列名；`None` 表示用契约解析 |

- 返回值：`DataCursor` 实例

---

### 函数名
`from_rows(cls, rows_by_source: Mapping[Hashable, List[Dict[str, Any]]], *, time_field_overrides: Optional[Mapping[Hashable, Optional[str]]] = None) -> DataCursor`

- 状态：`stable`
- 描述：类方法；无 **`DataContract`**，直接按行列表建游标；默认时间字段 **`"date"`**（可被 overrides）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `rows_by_source` | `Mapping[Hashable, List[Dict[str, Any]]]` | 每源行数据 |
| `time_field_overrides` (可选) | `Optional[Mapping[Hashable, Optional[str]]]` | 每源时间列 |

- 返回值：`DataCursor`

---

### 函数名
`reset(self) -> None`

- 状态：`stable`
- 描述：所有源游标与累计缓冲清零。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`until(self, as_of: str) -> Dict[Hashable, List[Dict[str, Any]]]`

- 状态：`stable`
- 描述：将各时序源推进到 **`as_of`（含）** 的 **累计前缀**；非时序源返回全量行。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `as_of` | `str` | 日期字符串，规范化后为 `YYYYMMDD` |

- 返回值：源键 → 行列表

---

## DataCursorManager

### 函数名
`create_cursor(self, name: str, contracts: Mapping[Hashable, DataContract], *, time_field_overrides: Optional[Mapping[Hashable, Optional[str]]] = None) -> DataCursor`

- 状态：`stable`
- 描述：创建 **`DataCursor`** 并以 **`name`** 注册。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 会话名 |
| `contracts` | `Mapping[Hashable, DataContract]` | 契约映射 |
| `time_field_overrides` (可选) | `Optional[Mapping[Hashable, Optional[str]]]` | 时间列覆盖 |

- 返回值：`DataCursor`

---

### 函数名
`create_cursor_from_rows(self, name: str, rows_by_source: Mapping[Hashable, List[Dict[str, Any]]], *, time_field_overrides: Optional[Mapping[Hashable, Optional[str]]] = None) -> DataCursor`

- 状态：`stable`
- 描述：**`DataCursor.from_rows`** 并注册。
- 诞生版本：`0.2.0`
- params：见 **`from_rows`**，外加 **`name`**。

- 返回值：`DataCursor`

---

### 函数名
`get_cursor(self, name: str) -> DataCursor`

- 状态：`stable`
- 描述：按名取游标；不存在 **`KeyError`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 会话名 |

- 返回值：`DataCursor`

---

### 函数名
`reset_cursor(self, name: str) -> None`

- 状态：`stable`
- 描述：对名下游标调用 **`reset()`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 会话名 |

- 返回值：`None`

---

### 函数名
`drop_cursor(self, name: str) -> None`

- 状态：`stable`
- 描述：移除注册（无则静默）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 会话名 |

- 返回值：`None`

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
