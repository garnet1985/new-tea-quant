## 列式存储与模拟器重构设计（MVP）

### 1. 目标与范围

**总体目标**

1. 在不改变现有业务语义（策略、枚举器、Scanner）的前提下，为回测/模拟链路引入列式存储基础设施，降低内存占用与 CPU 开销。
2. 为后续引入 Parquet（作为枚举结果的高效持久化格式）预留接口，但不在 MVP 阶段强制双写。

**本次改造只覆盖：**

- **内存数据结构**：模拟过程中的机会、目标、事件、依赖数据的承载方式。
- **数据读取路径**：
  - DB → `StrategyWorkerDataManager`（历史/依赖数据）；
  - SOT CSV → `DataLoader` → PriceFactor / CapitalAllocation。
- **输出路径（可选）**：在写 JSON 结果前的内存结构转换方式。

**明确不改动的部分（MVP 阶段）：**

- DB 基础设施与 `DbBaseModel` 默认返回类型（仍为 `List[Dict]`）。
- 枚举器（Layer 0）的职责与 CSV 输出格式（Parquet 支持作为后续阶段）。
- StrategyManager、Scanner、StrategyWorker 对外接口与钩子语义。

---

### 2. 核心数据抽象设计

#### 2.1 ColumnarTable

**职责**：在内存中以**列式**方式承载一张表的数据，用于减少重复的 dict 结构开销，并为按列/按行访问提供统一接口。

**数据结构（示意）**

```python
class ColumnarTable:
    headers: list[str]                 # 字段名列表
    columns: dict[str, list[object]]   # 每列一个 list，长度一致
    size: int                          # 行数（只读属性）

    def row_view(self, idx: int) -> "RowView": ...
    def iter_rows(self, start: int = 0, end: int | None = None) -> Iterable["RowView"]: ...
    def get_column(self, name: str) -> list[object]: ...
```

实现要点：

- 内部一律使用列式存储：`columns[field][row_idx]`，不再保存 `List[Dict]`。
- `size` 为只读属性，保证 `len(columns[field])` 一致性。
- 禁止在 `ColumnarTable` 上暴露可变的行级写接口（避免误用导致结构不一致），写操作集中在构建阶段。

#### 2.2 RowView / RowSeq

**RowView 职责**：为单行提供“看起来像 dict 的只读视图”，兼容现有钩子与 builder。

```python
class RowView(Mapping[str, object]):
    table: ColumnarTable
    index: int

    def __getitem__(self, key: str) -> object: ...
    def get(self, key: str, default: object | None = None) -> object | None: ...
    def keys(self) -> Iterable[str]: ...
    def to_dict(self) -> dict[str, object]: ...  # 按需 materialize
```

约定：

- RowView 至少支持：
  - `row["field"]`
  - `row.get("field")`
  - `for k in row.keys()`
- 不保证 `isinstance(row, dict)` 成立，文档中会明确这一点。

**RowSeq（可选）**：为某个行区间提供迭代视图：

```python
class RowSeq(Iterable[RowView]):
    table: ColumnarTable
    start: int
    end: int  # [start, end)
```

---

### 3. 时序专用抽象：ColumnarTimeSeries

**职责**：在 `ColumnarTable` 之上，提供按日期推进游标、获取“截至某日的所有数据”的能力，用于策略 Worker 与资金分配模拟器。

**数据结构（示意）**

```python
class ColumnarTimeSeries(ColumnarTable):
    date_col: str = "date"
    cursor: int = -1  # 已消费到的最后一行索引

    def advance_until(self, date_of_today: str) -> int: ...
    def iter_until_cursor(self) -> Iterable[RowView]: ...
```

行为约定：

- `advance_until(date)`：
  - 在保证 `date_col` 已排序的前提下，将 `cursor` 推进到最后一个 `date <= date_of_today` 的行；
  - 返回新的 `cursor` 索引。
- `iter_until_cursor()`：
  - 迭代 `[0 .. cursor]` 范围内的 RowView，不复制底层列数据。

游标与累积数据不再通过 `{'cursor': int, 'acc': list}` 管理，而是只依赖：

- `ColumnarTimeSeries.cursor`（游标位置）
- RowView 视图（需要行时再按索引访问）

---

### 4. DB 读取路径中的转换策略

本次 MVP 不修改 DB 模型默认返回类型（仍为 `List[Dict]`），而是按照“**尽量靠近消费者**”的原则，在以下两条路径上完成行→列转换：

1. **策略 Worker 历史/依赖数据（K 线 + 财务等）**
2. **模拟器读取 SOT（opportunities/targets）**

#### 4.1 策略 Worker：StrategyWorkerDataManager

当前行为（简化）：

- `_load_klines` / `_load_entity`：
  - 从 DataManager/DB 拉取 `List[Dict]`；
  - 存入 `self._current_data[entity_type] = data_list`。
- 游标逻辑：
  - `_cursor_state[entity_type] = {'cursor': -1, 'acc': []}`
  - `_advance_cursor_until(data_list, state, ...)` 中 append 到 `acc`。

改造方向：

- `_current_data[entity_type]` 存储 `ColumnarTimeSeries` 而非 `List[Dict]`。
- `_cursor_state` 仅保存游标信息（或直接使用 `ColumnarTimeSeries.cursor`），不再保存 `acc` 列表。
- `get_data_until(date)`：
  - 对每个 `ColumnarTimeSeries` 调用 `advance_until(date)`；
  - 对策略 Worker 提供：
    - 兼容模式：返回 `List[Dict]`（通过 `RowView.to_dict()` materialize，逐步迁移）；
    - 新模式（长期）：返回 `RowSeq` 或 `ColumnarTimeSeries` 视图。

#### 4.2 模拟器：DataLoader → PriceFactor / CapitalAllocation

当前行为（简化）：

- `DataLoader._load_opportunities_from_file` / `_load_targets_from_file`：
  - 使用 `csv.DictReader` 读入 `List[Dict]`；
  - `load_opportunities_and_targets` 返回 `(List[Dict], Dict[str, List[Dict]])`。
- `PriceFactorSimulatorWorker`：
  - 直接在 `List[Dict]` 上排序与遍历。
- `CapitalAllocationSimulator`：
  - `build_event_stream` 构造 `List[Event]`，每个 `Event` 持有 `opportunity: Dict` 与 `target: Dict`。

改造方向：

- DataLoader 中新增**模拟器专用**列式加载 API（初期可标记为内部使用）：

  ```python
  def load_for_simulator_columnar(
      self,
      output_version_dir: Path,
      stock_id: str | None,
      start_date: str = "",
      end_date: str = "",
  ) -> tuple[ColumnarTable, ColumnarTable, dict[str, list[int]]]:
      """
      返回:
        - opportunities_table: ColumnarTable
        - targets_table: ColumnarTable
        - targets_index: {opportunity_id: [row_idx, ...]}
      """
  ```

- PriceFactor / CapitalAllocation 在内部改用 ColumnarTable + RowView 进行遍历与钩子调用，最终在写 JSON 时再 materialize 为 `List[Dict]`。

---

### 5. Parquet 支持（后续阶段预留）

**MVP 阶段策略：**

- 不立即引入双写，只在 DataLoader 设计中预留“优先读 Parquet、缺失时回退 CSV”的能力。
- 当枚举结果规模足够大、I/O 成为瓶颈时，再对枚举器 Worker 增加：
  - Parquet 输出（基于 ColumnarTable 或临时 DataFrame/Arrow）；
  - 配置项控制 CSV/Parquet 的启用与否。

**长期目标：**

- SOT 结果以 Parquet 为主格式，CSV 作为可读/调试工具；
- 内存中统一通过 ColumnarTable 承载，不依赖具体落盘格式。

---

### 6. TODO 列表（按优先级）

#### P0：列式基础设施 + 模拟器内部改造

1. **实现 ColumnarTable 与 RowView**
   - 定义数据结构与接口；
   - 支持 `row["field"]` / `row.get("field")` / `dict(row)`。

2. **实现 ColumnarTimeSeries（继承或组合 ColumnarTable）**
   - 字段：`date_col`, `cursor`；
   - 方法：`advance_until(date)`, `iter_until_cursor()`。

3. **在 StrategyWorkerDataManager 中接入 ColumnarTimeSeries**
   - `_load_klines` / `_load_entity` 之后，将 `List[Dict]` 转为 ColumnarTimeSeries；
   - `_cursor_state` 简化为仅保存游标（或直接使用 TS 内部游标）；
   - `get_data_until` 使用 `advance_until`，对外先保留 `List[Dict]` 兼容输出（通过 RowView.to_dict）。

4. **在 DataLoader 中增加模拟器专用 columnar 加载 API**
   - 实现从 CSV → ColumnarTable 的读取；
   - 返回 opportunities/targets 的 ColumnarTable 以及 targets 索引。

5. **改造 PriceFactorSimulatorWorker 使用 ColumnarTable**
   - 使用新的 DataLoader API 获取列式机会/目标表；
   - 在 `_simulate_one_share_per_opportunity` 中使用 RowView 遍历；
   - 在写 JSON 前将结果 RowView 序列 materialize 为 `List[Dict]`。

6. **（可选，同一阶段或下一阶段）改造 CapitalAllocationSimulator 使用 ColumnarTable + 简化 Event**
   - 事件只保存元信息和行索引，不再嵌入完整 dict；
   - 在处理事件时按需通过 RowView 访问 opportunity/target 内容。

#### P1：Parquet 支持（后续阶段）

7. **在 DataLoader 中预留 Parquet 读取分支**
   - 定义：如果存在 `*.parquet`，优先读 Parquet 构建 ColumnarTable，否则读 CSV。

8. **在枚举器 Worker 中增加 Parquet 输出能力**
   - 在现有 CSV 输出基础上增加 Parquet 写入（可配置开关）；
   - 确保目录结构与 VersionManager 兼容。

9. **配置与文档更新**
   - 在策略 settings 或全局配置中增加 SOT 输出格式开关；
   - 在 README/架构文档中说明：
     - Columnar 内存结构的存在；
     - Parquet 的使用建议与适用场景。

---

### 7. 验证与回归

1. 使用 `example` 策略在典型时间区间上跑：
   - 枚举 → PriceFactor → CapitalAllocation 全链路；
   - 比较改造前后：
     - 机会数量、投资/交易数量；
     - 收益率、最大回撤等关键指标是否一致。
2. 在较大样本（多策略、多年份）上对比：
   - 峰值内存占用；
   - PriceFactor / CapitalAllocation 的整体执行时间。

验证通过后，再考虑将 ColumnarTable 抽象在更多模块（如 DataSource handler、Tag 等）中推广复用。

