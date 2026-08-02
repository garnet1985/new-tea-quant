# Utils 详细设计

**版本：** `0.2.0`

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅 `Utils` Facade | 消除 deep-import |
| 命名空间 | date / types / io / math | 对应原子包职责 |
| 原 `Utils` 类 | 改名 `TypeUtils` → `Utils.types` | 避免与 Facade 同名 |
| 原 `DateUtils` | 保留实现类，公开为 `Utils.date` | 迁移成本最低 |
| 公开稳定性 | 最高 `beta` | core `0.x` |

## 实现备注

- `date` 内部拆 `parser` / `calculator` / `period` / `constants`
- `types` 的 pandas 依赖仅在 DataFrame 方法内 import
- `math.deterministic_unit_float`：SHA-256 → `[0,1)`，可复现

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
