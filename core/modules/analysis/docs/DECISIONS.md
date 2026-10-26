# modules.analysis — 决定

**版本：** `0.1.0`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：设计点 1：独立模块还是放进 strategy

- **采用：** 方案 A
- **理由：** 与 BE / strategy 的「调度 vs 业务」分离同一原则；空模块成本可接受
- **影响：** `Strategy.analyze` 与 CLI `strategy_analyse` / `sy` 已删除；归因只进本模块

---

---

## DEC-02：设计点 2：与 factor 模块分家

- **采用：** analysis 不提供因子研究 API；不在本模块预埋 IC / 滚动 / 挖掘入口
- **理由：** 问题不同；工具以后可以共享统计原语，产品入口必须分开
- **影响：** 本模块 glossary 将「因子」列为 avoid

---

---

## DEC-03：设计点 3：如何判断 inputs（待决）

- **采用：** 待决
- **理由：** 还没有判定规则，也没有约定策略必须把现场值写入产物
- **影响：** 行为 API 不能先写「factor_cols=...」这类参数

---

---

## DEC-04：设计点 4：如何归因（待决）

- **采用：** 待决
- **理由：** 方法取决于 inputs 怎么定义；先定对象再定算法
- **影响：** Facade 暂无 `attribute` / `compare` 方法，避免先锁 API

---

---

## DEC-05：设计点 5：解释结果要不要分三层（待决）

- **采用：** 待决
- **理由：** 取决于第一期要回答哪一句话；不要因为模拟分三层就默认分析也分三层

---


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
