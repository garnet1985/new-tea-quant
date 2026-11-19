# Analysis（`modules.analysis`）

**模块：** `modules.analysis` · **版本：** `0.1.0`

**最低支持核心版本：** `>=0.5.0`

## 简介

纯数学计算工具箱。输入一列数字，输出分桶、相关性、回归等统计结果——不读文件、不管业务、也不写报告文案。策略回测的归因解释不走这里，那是 `strategy/engines/analyzer` 的事。

## 适用场景

- 策略跑完了，想算一下因子分桶、收益率相关性、回归系数
- 给因子做 IC、滚动窗口等统计时，不想自己写 pandas 代码

## 模块依赖

无硬依赖（运行需 Python `pandas`；ML 部分可选 `scikit-learn`）

## 设计初衷

- **要解决的问题：** 把"纯数学"和"业务归因"分开——业务归因读策略产物、管文案；本模块只做数字计算。
- **明确不做：** 不读回测文件、不管配置、不产生报告；不做全市场因子挖掘。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [概念](./docs/CONCEPTS.md)
- [决策](./docs/DECISIONS.md)
