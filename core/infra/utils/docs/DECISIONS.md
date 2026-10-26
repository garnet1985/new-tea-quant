# infra.utils — 设计与决策

**版本：** `0.2.2`

本文记录 infra.utils 模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

提供项目级原子工具集（日期、类型、IO、数学、markdown、locale、包源），消除调用方 deep-import，公开面与其它 infra 模块保持一致；core `0.x` 阶段公开稳定性不超过 `beta`。

## 方案与思路

- **单一 Facade 收口：** 对外只导出 `Utils` Facade；命名空间按原子包职责划分（date / types / io / math / markdown / locale / pkg）。原 `Utils` 类改名 `TypeUtils` 挂到 `Utils.types` 避免与 Facade 同名；原 `DateUtils` 保留实现类、公开为 `Utils.date`。
- **实现备注：**
  - `date` 内部拆 `parser` / `calculator` / `period` / `constants`；解析与季度辅助以 `parser` 为单一来源。
  - `types` 的 pandas 依赖仅在 DataFrame 方法内 import。
  - `math.deterministic_unit_float`：SHA-256 → `[0,1)`，可复现。
  - `locale.is_china`：认大陆 IANA 地名（`Asia/Shanghai` 等）或 `zh_CN`，**不用** UTC+8；不含网络探测。
  - `pkg`：pip / npm 依赖源。`USE_CHINA_MIRROR` → `is_china` → pypi 探活。国内默认中科大（可换源）+ npmmirror。
  - 无界查询下界 `get_query_date_range_min` 仍读配置；业务「默认开始日」请用 `ProjectContext.config`。

具体拍板见下文 DEC-01。

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

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
