# Analysis（`modules.analysis`）

回测完成后，解释**这一次（或少数几次）策略 run** 的 inputs 与 outputs 有多大关系。对外门面为 `Analysis`。

当前是空骨架：可以 import，没有可调用的归因行为。三个核心问题仍未拍板，见设计文档。

## 适用场景

- 一次 enumerate / price_factor / portfolio 跑完后，想理解结果在多大程度上来自声明过的输入
- 对照两次只改了旋钮的 run，看输出差在哪
- 明确不用于：全市场因子挖掘、滚动 IC、股票分组研究平台（那是未来的 factor 模块）

## 模块依赖

无（骨架）。预计日后只读 `modules.strategy` 的公开产物路径，不依赖 backtest_engine。

## 设计初衷

- **要解决的问题：** 现有各层 report 只描述结果长什么样，不解释结果和 inputs 的关系。
- **明确不做：** 不跑回测、不另起时间轴、不建因子库。`modules.strategy` 不提供 analyze API。

## 常见问题

**Q：现在能算归因吗？**  
A：不能。先把「如何认定 inputs / 如何归因 / 如何解释三层结果」想清楚，再加行为 API。

**Q：和 strategy 里的报告是什么关系？**  
A：strategy 生产并展示模拟产物；本模块消费产物做解释。二者不要重复计算胜率、净值这类总数。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [概念与运作](./docs/CONCEPTS.md)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
