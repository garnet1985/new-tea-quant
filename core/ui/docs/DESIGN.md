# UI 设计说明

**模块：** `ui` · **版本：** `0.2.3`

已定结论见 [ARCHITECTURE.md](./ARCHITECTURE.md)。全页引导的步骤关系见 [CONCEPTS.md](./CONCEPTS.md)。前端目录和命名见模块根的 `FED_STANDARD.md`。过程稿在 [notes/](./notes/)，不作为契约。

---

## 策略设置表单

调试页里，`core` 用原始 dict 编辑。其余块由策略设置的 editorSchemas 驱动。没出现在表单里的字段原样保留。

早期字段表（时间窗写在 `simulation.start_date`、并建议由该表生成 schema）已经和现行表单不一致。那份表在 [notes/strategy-workbench-settings-schema-v1.md](./notes/strategy-workbench-settings-schema-v1.md)。

---

## 启动入口

用户只有 `python launcher.py`：检查环境、按需安装、再拉起 BFF 和 FED。安装脚本不是日常入口。过程稿里的分阶段清单在 [notes/launcher-and-setup-runtime-design.md](./notes/launcher-and-setup-runtime-design.md)。
