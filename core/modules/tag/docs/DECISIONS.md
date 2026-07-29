# Tag 设计决策

**版本：** `0.4.1`

仅保留仍有效的决策。已废弃的 JobPipeline / BaseTagWorker / 模块内 CLI 决策不再收录。

---

## 决策 1：按 `data.base` 分流调度（BE vs 轻量主进程）

**背景**  
`entity_based` / `slice_based` 只在「多个实体」时有排程差异。global / 非时序没有多实体宇宙，硬塞进 BacktestEngine 没有收益。

**决策**  
路由只看 **`settings.data.base` 对应 contract 的 `scope × type`**：

| base | 调度 | `calculation.execution.mode` |
|------|------|------------------------------|
| **per_entity**（时序） | **BacktestEngine**（`entity_based` / `slice_based` 多进程） | 必填，含义见决策 3 |
| **global**（时序） | **Tag 轻量主进程推进器**（不走 BE） | **忽略**；若配置了则 **warning** |
| **non_time_series** | **Tag 轻量主进程**（一次性/极少次，不走 BE） | **忽略**；若配置了则 **warning** |

- per_entity：JobBuilder / JobExecutor + flush；并行与 Timeline/Slice 由 BE 负责；调参走 `worker.json` → `job_pipeline.tag`
- global / non_ts：**不**进 BE，**不**做 mode→BE 映射或探针；Tag 自备主进程 runner（装数 → 推进/一次计算 → flush / progress）
- 禁止再引入旧 JobPipeline / BaseTagWorker；CLI 仍在 `core/infra/cli`

**后果**  
- Facade 按 base 元数据分发 pipeline / runner  
- global 实体池为哨兵（如 `__global__`），progress / value 仍用同一套表  

---

## 决策 2：增量水位用 last_calculated_end

**背景**  
用 `max(as_of_date)` 做水位会在「变更才写」类标签上错误跳过区间。

**决策**  
每实体进度存 `sys_tag_calc_progress.last_calculated_end`（经 `TagDataService`）；成功且非 dry_run 时推进。`calculated_at` / `scenario.updated_at` 仅元数据，不作业务水位。

**后果**  
UI 列表的 `last_computed_as_of`（`get_max_as_of_date`）可以与增量水位不同，属展示字段。global 哨兵同样用该水位。

---

## 决策 3：entity_based vs slice_based（仅 per_entity）

**背景**  
时序打标与横截面打标数据形态不同；二者都是 **多实体** 下的排程选择。

**决策**  
仅当 `data.base` 为 **per_entity** 时：

- `entity_based` + `calculate_tag`：各实体按各自时间线推进  
- `slice_based` + `on_calendar_asof`：日历横切  

二者在 `update_mode=incremental` 时都读写 `sys_tag_calc_progress`；`refresh` / `recompute` 清 progress，跑完不回写水位。

global / non_ts **不适用** 本决策；不提供同等 `execution.mode` 语义（见决策 1）。  
手写 `tag_target_type=general` stub 不再作为产品入口；宇宙由 base 的 scope 推断。

---

## 决策 4：Facade 名称为 Tag

**背景**  
迁移期保留 `TagManager` shim。

**决策**  
对外唯一入口为 `Tag`；`TagManager` / `run_tag` / 模块 `__main__` 已删除。BFF 经 `TagCatalog` / `TagRunLauncher`。

---

## 决策 5：Tag 表字段单一真相

**背景**  
`sys_tag_value` 曾重复 `attach_to_data_key`，且写入路径使用未在 schema 声明的 `entity_type`。

**决策**  
- `attach_to_data_key` SOT = `sys_tag_scenario`；读 value 时 JOIN scenario  
- `sys_tag_value` / `sys_tag_calc_progress` 不存 `entity_type`（实体族由 scenario / base 的 `list_data_key` 等推断）  
- frontier = progress.`last_calculated_end`；value 的 as_of / calculated_at 不作水位
