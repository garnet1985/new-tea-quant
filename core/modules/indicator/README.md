# Indicator（`modules.indicator`）

为 New Tea Quant（简称 **NTQ**）提供技术指标计算。对外门面为 `Indicator`（pandas-ta-classic 薄代理）；结果类型见 `contracts`。词条见 [glossary.yaml](./glossary.yaml)。

策略里 `settings.data.indicators` 的命名与参数约定见 [AVAILABLE_INDICATORS.md](./AVAILABLE_INDICATORS.md)。

## 适用场景

- Strategy / Tag / 分析脚本中对 K 线序列算 MA、RSI、MACD 等
- 通过 `Indicator.calculate('cci', klines, ...)` 调用库内任意已实现指标

## 模块依赖

无 NTQ 模块硬依赖；运行需 `pandas`、`pandas-ta-classic`。

## 设计初衷

- **要解决的问题：** 统一 List[Dict] K 线与 TA 库之间的格式桥接。
- **明确不做：** 不缓存结果、不 fork 指标公式、不做跨股票批量编排。

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.indicator import Indicator`；类型 `from core.modules.indicator.contracts import BatchIndicatorResult`。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
