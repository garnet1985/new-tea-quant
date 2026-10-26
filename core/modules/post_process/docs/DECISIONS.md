# post_process — 决定

**版本：** `0.3.0`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：协议与编排分离

**是什么：** 三层协议只描述扫描出口；干活在 Component。

**放弃了什么：** 把协议字段直接塞进 Component 的输出里

## DEC-02：PostProcess 不是 pipeline

**是什么：** 声明无序；执行序仅由依赖拓扑决定。

**放弃了什么：** 把 Component 做成流水线、前一步输出作为下一步输入

## DEC-03：一策略一份 StrategyScanReport

**是什么：** 多策略联合扫描时，每个策略一份 StrategyScanReport，会话顶层用 ScanSessionReport.strategies 集合。

**放弃了什么：** 把所有策略机会扁平成一份大报告

## DEC-04：不兼容旧 adapters 目录

**是什么：** 过时的 BaseOpportunityAdapter / scanner.adapters 已删除；所有后续处理走 PostProcess Dispatcher。

**放弃了什么：** 为旧 adapters 目录保留兼容层

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
