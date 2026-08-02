# Utils 架构文档

**版本：** `0.2.0`

## 模块介绍

`infra.utils` 提供与业务无关的通用工具，经 Facade `Utils` 暴露。

## 架构

```text
Utils
  ├── date   → date/date_utils.DateUtils
  ├── types  → type_utils.TypeUtils
  ├── io     → io/csv_io + io/file_io
  └── math   → math/deterministic_random
contracts    → PERIOD_* / PeriodType / ArchiveFormat
```

## 边界

**In scope：** 日期、类型判断、CSV/归档、确定性随机  
**Out of scope：** 配置合并（`ProjectContext`）、CLI 图标（`CmdLayout`）、业务日历规则（`CalendarService`）

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
