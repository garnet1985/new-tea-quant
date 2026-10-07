# UI 设计说明

**模块：** `ui` · **版本：** `0.2.3`

已定结论见 [ARCHITECTURE.md](./ARCHITECTURE.md)。全页引导的步骤关系见 [CONCEPTS.md](./CONCEPTS.md)。过程稿在 [notes/](./notes/)，不作为契约。

---

## 源文件命名

目录、`.js` / `.jsx` / `.scss` 用小写开头的驼峰，例如 `strategyListPage.js`、`appNavigation.js`。不用帕斯卡式文件名，以免和组件符号混在一起。

同一功能拆成多个文件时，用点号连接职责，主体名仍是小写驼峰：`strategy.test.js`、`strategy.helper.js`。页面主文件默认合并成一个驼峰词，例如 `strategyListPage.js`，不写成 `strategyList.page.js`。

类、类型、枚举，以及在 JSX 里使用的函数组件名，用帕斯卡。普通函数、变量、hook 用驼峰。文件名不必和组件名逐字相同：`strategyListPage.js` 里导出 `StrategyListPage` 是正常写法。

样式 class 用 kebab-case。与组件同目录的样式跟 JS 同名，例如 `strategyListPage.scss`。

---

## 策略设置表单

调试页里，`core` 用原始 dict 编辑。其余块由 `fed/src/pages/strategyWorkbenchPage/panels/strategySettingsPanel/editorSchemas/` 驱动。没出现在表单里的字段原样保留。

早期字段表（时间窗写在 `simulation.start_date`、并建议由该表生成 schema）已经和现行表单不一致。那份表在 [notes/strategy-workbench-settings-schema-v1.md](./notes/strategy-workbench-settings-schema-v1.md)。

---

## 启动入口

用户只有 `python launcher.py`：检查环境、按需安装、再拉起 BFF 和 FED。安装脚本不是日常入口。过程稿里的分阶段清单在 [notes/launcher-and-setup-runtime-design.md](./notes/launcher-and-setup-runtime-design.md)。
