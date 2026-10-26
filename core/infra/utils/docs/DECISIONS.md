# infra.utils — 决定

**版本：** `0.2.2`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：决策摘要

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅 `Utils` Facade | 消除 deep-import |
| 实现位置 | `core/` | 与其它 infra 模块一致 |
| 命名空间 | date / types / io / math / markdown / locale / pkg | 对应原子包职责 |
| 原 `Utils` 类 | 改名 `TypeUtils` → `Utils.types` | 避免与 Facade 同名 |
| 原 `DateUtils` | 保留实现类，公开为 `Utils.date` | 迁移成本最低 |
| IO / math | 类方法（`CsvIo` / `FileIo` / `DeterministicRandom`） | 禁止导出自由函数 |
| 公开稳定性 | 最高 `beta` | core `0.x` |


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
