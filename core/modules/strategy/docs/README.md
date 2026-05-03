# 策略模块文档（新骨架）

本目录存放 `core/modules/strategy` 的架构说明、契约与迁移笔记。

## 决策记录

- `decisions/001-enumerator-reuse-by-containment.md`：基于包含关系与差量股票的枚举复用策略。

## 专题说明

- `output-slice.md`：`StrategyOutputReaderService.load_opportunity_snapshot(...)` 请求与响应约定。
- `settings-fingerprint-policy.md`：settings 规范形态、工作台 **`settings_core`** 各字段是否参与指纹、以及（历史）枚举器指纹块级策略。
- `workbench-version-fingerprint.md`：工作台快照版本身份因子（`settings_core`、范围、引擎版本、策略代码哈希）及指纹载荷约定。
