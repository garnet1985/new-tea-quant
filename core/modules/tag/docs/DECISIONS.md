# tag — 决定

**版本：** `0.4.0`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：按 data.base 分流（BE vs 主进程）

**是什么：** per_entity 进 BacktestEngine；global / non_time_series 用 Tag 轻量主进程推进器，忽略 execution.mode。

**为什么选它：** per_entity 需要 K 线，走 BE 调度；global 只需一次主进程遍历，不值得拉起 BE。

## DEC-02：增量水位用 last_calculated_end

**是什么：** 每实体 progress 存 last_calculated_end，非 max(as_of_date)。

## DEC-03：entity_based vs slice_based（仅 per_entity）

**是什么：** entity_based + calculate_tag；slice_based + on_calendar_asof。

## DEC-04：Facade 名称为 Tag

**是什么：** 对外唯一入口 Tag；BFF 经 TagCatalog / TagRunLauncher。

## DEC-05：Tag 表字段单一真相

**是什么：** attach_to_data_key SOT = sys_data_tag_scenario；progress 水位用 last_calculated_end。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
