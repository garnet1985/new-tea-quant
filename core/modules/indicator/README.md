# Indicator（`modules.indicator`）

**模块：** `modules.indicator` · **版本：** `0.2.0`

## 简介

技术指标计算器。给一串 K 线数据，算 MA、RSI、MACD、KDJ 等常用指标。策略里写 `settings.data.indicators` 或在代码里调 `Indicator.calculate('macd', klines)` 就行。

## 适用场景

- 策略里配了技术指标，回测时自动算出来给后续逻辑用
- 分析脚本里临时算一下 MACD、BOLLINGER 带看看形态

## 模块依赖

无硬依赖（运行需 Python `pandas`、`pandas-ta-classic`）

## 设计初衷

- **要解决的问题：** 把 K 线格式和 TA 库桥接起来，策略不用自己写格式转换。
- **明确不做：** 不缓存结果、不改指标公式、不做跨股票批量编排。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [可用指标清单](./docs/AVAILABLE_INDICATORS.md)
- [快速开始](./QUICKSTART.md)
- [设计](./docs/DESIGN.md)
- [决策](./docs/DECISIONS.md)
