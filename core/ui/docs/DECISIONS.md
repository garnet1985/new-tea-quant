# UI — 设计与决策

**版本：** `0.2.3`

本文记录本模块的设计目标、方案思路与拍板决策。已定结论见 [ARCHITECTURE.md](./ARCHITECTURE.md)，全页引导的步骤关系见 [CONCEPTS.md](./CONCEPTS.md)。

---

## 设计目标

- 让桌面 UI 的策略设置表单随策略定义自动演化，不为每个策略手写表单。
- 让用户日常启动只有一条路径，避免多入口带来的支持成本。

## 方案与思路

**策略设置表单：** 调试页里，`core` 用原始 dict 编辑，其余块由策略设置的 editorSchemas 驱动；没出现在表单里的字段原样保留。早期曾维护过一份字段表（时间窗写在 `simulation.start_date`、并建议由该表生成 schema），已与现行表单不一致并废弃，留档在 [notes/strategy-workbench-settings-schema-v1.md](./notes/strategy-workbench-settings-schema-v1.md)。

**启动入口：** 用户只有 `python launcher.py`：检查环境、按需安装、再拉起 BFF 和 FED。安装脚本不是日常入口。过程稿里的分阶段清单在 [notes/launcher-and-setup-runtime-design.md](./notes/launcher-and-setup-runtime-design.md)。

---

## DEC-01：策略设置表单由 editorSchemas 驱动

**是什么：** 调试页中 `core` 块用原始 dict 编辑，其余块由策略设置的 editorSchemas 驱动；未出现在表单中的字段原样保留。

**为什么选它：** 表单随策略定义自动演化，新增策略无需手写表单；未覆盖字段不丢失。

**放弃了什么：** 由早期字段表生成 schema 的做法 — 已与现行表单不一致，废弃（留档见 notes/）。

## DEC-02：日常启动入口唯一（launcher.py）

**是什么：** 用户侧只有 `python launcher.py` 一个入口，环境检查、按需安装、拉起 BFF/FED 全部收敛进去。

**为什么选它：** 单一入口降低使用与支持成本。

**放弃了什么：** 把安装脚本作为日常入口 — 安装脚本保留但不是日常路径。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [概念](./CONCEPTS.md)
- [README](../README.md)
