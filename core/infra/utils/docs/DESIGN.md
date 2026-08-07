# Utils 详细设计

**版本：** `0.2.0`

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅 `Utils` Facade | 消除 deep-import |
| 实现位置 | `core/` | 与其它 infra 模块一致 |
| 命名空间 | date / types / io / math / markdown | 对应原子包职责 |
| 原 `Utils` 类 | 改名 `TypeUtils` → `Utils.types` | 避免与 Facade 同名 |
| 原 `DateUtils` | 保留实现类，公开为 `Utils.date` | 迁移成本最低 |
| IO / math | 类方法（`CsvIo` / `FileIo` / `DeterministicRandom`） | 禁止导出自由函数 |
| 公开稳定性 | 最高 `beta` | core `0.x` |

## 实现备注

- `date` 内部拆 `parser` / `calculator` / `period` / `constants`；解析与季度辅助以 `parser` 为单一来源
- `types` 的 pandas 依赖仅在 DataFrame 方法内 import
- `math.deterministic_unit_float`：SHA-256 → `[0,1)`，可复现
- 无界查询下界 `get_query_date_range_min` 仍读配置；业务「默认开始日」请用 `ProjectContext.config`

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
