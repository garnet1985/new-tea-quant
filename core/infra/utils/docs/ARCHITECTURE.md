# Utils 架构文档

**版本：** `0.2.0`

## 模块介绍

`infra.utils` 提供与业务无关的通用工具，经 Facade `Utils` 暴露。

## 架构

```text
Utils
  ├── date      → core/date/date_utils.DateUtils
  ├── types     → core/type_utils.TypeUtils
  ├── io        → core/io（CsvIo / FileIo）
  ├── math      → core/math/DeterministicRandom
  └── markdown  → core/markdown/MarkdownMgr
contracts       → PERIOD_* / PeriodType / ArchiveFormat
```

## 边界

**In scope：** 日期、类型判断、CSV/归档、确定性随机、MD 模版填充  
**Out of scope：** 配置合并（`ProjectContext`）、默认业务起止日（`ProjectContext.config.get_default_start_date`）、CLI 图标（`CmdLayout`）、业务日历规则（`CalendarService`）

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
