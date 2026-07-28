# Tag 设计决策

**版本：** `0.4.0`

仅保留仍有效的决策。已废弃的 JobPipeline / BaseTagWorker / 模块内 CLI 决策不再收录。

---

## 决策 1：调度交给 BacktestEngine

**背景**  
旧 Tag 自建 JobPipeline + ProcessWorker + BaseTagWorker，与 strategy 双轨。

**决策**  
Tag 只做 JobBuilder / JobExecutor（RunCallbacks）与 flush；并行与 Timeline/Slice 由 **BacktestEngine** 负责。性能与 strategy 一样走 **`worker.json` → `job_pipeline.tag`**（`dispatch` = entity_based，`calendar_slice` = slice_based）。

**后果**  
- 禁止再引入模块内 JobPipeline / BaseTagWorker  
- CLI 不在 tag 包内（`core/infra/cli`）  
- userspace `settings.performance` 忽略；调参改 `worker.json`（可 `userspace/config/worker.json` 覆盖）

---

## 决策 2：增量水位用 last_calculated_end

**背景**  
用 `max(as_of_date)` 做水位会在「变更才写」类标签上错误跳过区间。

**决策**  
每实体进度存 `sys_tag_calc_progress.last_calculated_end`（经 `TagDataService`）；成功且非 dry_run 时推进。`calculated_at` / `scenario.updated_at` 仅元数据，不作业务水位。

**后果**  
UI 列表的 `last_computed_as_of`（`get_max_as_of_date`）可以与增量水位不同，属展示字段。

---

## 决策 3：entity_based vs slice_based

**背景**  
时序打标与横截面打标数据形态不同。

**决策**  
- `entity_based` + `calculate_tag`：常规按实体推进  
- `slice_based` + `on_calendar_asof`：日历切片横截面  

二者在 `update_mode=incremental` 时都读写 `sys_tag_calc_progress`；`refresh` / `recompute` 清 progress，跑完不回写水位。

`general` 目标类型仅有 stub（`__general__`），不对 userspace 开放同等配置。

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
- `sys_tag_value` / `sys_tag_calc_progress` 不存 `entity_type`（当前默认 stock）  
- frontier = progress.`last_calculated_end`；value 的 as_of / calculated_at 不作水位
