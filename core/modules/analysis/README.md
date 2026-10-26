# Analysis（`modules.analysis`）

**模块：** `modules.analysis` · **版本：** `0.1.0`

统计 / ML 原语工具箱（纯函数、无业务、无 I/O）。输入列向量，输出分桶、相关、回归等统计结构。**不是**策略回测的归因解释——解释一次策略 run 的编排与产物在 `strategy/engines/analyzer`。

## 适用场景

- strategy 等模块需要对某列因子值做分桶、相关性、回归等纯数学计算时
- 日后可扩展 XGBoost / SHAP 等 ML 模块（均为纯函数）

## 模块依赖

无硬依赖
## 设计初衷

- **要解决的问题：** 把"数学原语"从"业务归因"中分离——业务归因读策略产物、管 report 文案；本模块只做数字计算。
- **明确不做：** 不读 `simulations/`、不管配置、不产生 report 文案；不做全市场因子挖掘（未来 factor 模块）。

## 常见问题

**Q：Facade 怎么用？**
A：行为 API 见 [API.md](./API.md)；纯函数直接调用 `core/classical/` 下对应函数即可。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
