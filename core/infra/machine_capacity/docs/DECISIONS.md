# infra.machine_capacity — 决定

**版本：** `0.2.1`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：D1：去掉旧字段兼容

不再识别 `main_process_reserve_mb`、`dispatch_memory_budget_mb`；只认 `memory_floor_mb` / `memory_budget_mb`。

---

## DEC-02：D2：门面承载全部实现

模块体量小，解析逻辑内联在 `MachineInfo`；不拆空 `core/` 包。


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
