# Analysis（`modules.analysis`）

**统计 / ML 原语工具箱**（无业务、无 I/O）。解释一次策略 run 的 **编排与产物** 在 `strategy/engines/analyzer`。

## 职责

- 提供分桶、相关、回归等 **纯函数**（输入列向量 → 输出统计结构）
- 后期：XGBoost / SHAP 等同模块 `core/ml/`
- **不提供：** 读 `simulations/`、step 配置、report 文案、simulate 调度

## 消费者

- `strategy/engines/analyzer` — AttributionPipeline stages
- 日后 factor 等模块可复用同一套数学，但不经过 strategy 产物路径

## 实施计划

见 [TODO.md](./TODO.md)（与 analyzer 侧 [TODO.md](../strategy/core/engines/analyzer/TODO.md) 四步对齐）。

## 当前状态

- Facade `Analysis` 仍为占位
- 行为 API 尚未导出；第二步起在 `core/classical/` 添加 stub

## 明确不做

- 全市场因子 IC / 滚动 / 挖掘（未来 factor 模块）
- 重复 strategy overall 报告中的胜率、净值

## 相关文档

- [TODO.md](./TODO.md) — **当前权威实施清单**
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) — 部分表述待与 TODO 同步
- [API.md](./API.md) — 行为 API 定稿后更新
