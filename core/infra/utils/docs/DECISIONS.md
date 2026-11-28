# infra.utils — 设计与决策

**模块：** `infra.utils` · **版本：** `0.2.3`

**最低支持核心版本：** `>=0.5.0`

本文记录 infra.utils 模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

提供项目级原子工具集（日期、类型、IO、数学、markdown、locale、包源），消除调用方 deep-import，公开面与其它 infra 模块保持一致；core `0.x` 阶段公开稳定性不超过 `beta`。

## 方案与思路

- **单一 Facade 收口：** 对外只导出 `Utils` Facade；命名空间按原子包职责划分（date / types / io / math / markdown / locale / pkg）。原 `Utils` 类改名 `TypeUtils` 挂到 `Utils.types`；原 `DateUtils` 保留实现类、公开为 `Utils.date`。
- **实现备注：** `date` 拆 parser / calculator / period；`types` 的 pandas 仅在 DataFrame 方法内 import；`locale.is_china` 不认 UTC+8；`pkg` 国内镜像链路与 `USE_CHINA_MIRROR` 见 USER_GUIDE。

具体拍板见下文 DEC-01。

---

## DEC-01：Facade 与命名空间

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅 `Utils` Facade | 消除 deep-import |
| 实现位置 | `core/` 子包 | 与其它 infra 一致 |
| 命名空间 | date / types / io / math / markdown / locale / pkg | 对应原子包职责 |
| 原 `Utils` 类 | 改名 `TypeUtils` → `Utils.types` | 避免与 Facade 同名 |
| 原 `DateUtils` | 实现类保留，公开为 `Utils.date` | 迁移成本最低 |
| IO / math | 类静态方法 | 不导出自由函数 |
| 公开稳定性 | 最高 `beta` | core `0.x` |

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)