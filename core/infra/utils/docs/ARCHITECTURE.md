# Utils 架构文档
**版本：** `0.2.2`

## 架构图

`infra.utils` 提供与业务无关的通用工具，经 Facade `Utils` 暴露。

```text
Utils
  ├── date      → core/date/date_utils.DateUtils
  ├── types     → core/type_utils.TypeUtils
  ├── io        → core/io（CsvIo / FileIo）
  ├── math      → core/math/DeterministicRandom
  ├── markdown  → core/markdown/MarkdownMgr
  ├── locale    → core/locale/LocaleUtils（is_china）
  └── pkg       → core/pkg_index/PkgIndex（pip / npm 镜像）
contracts       → PERIOD_* / PeriodType / ArchiveFormat
```

## 职责与边界（结论）

**In scope：** 日期、类型判断、CSV/归档、确定性随机、MD 模版填充、本机区域（`is_china`）、pip/npm 依赖源（`pkg`）  
**Out of scope：** 配置合并（`ProjectContext`）、默认业务起止日（`ProjectContext.config.get_default_start_date`）、CLI 图标（`CmdLayout`）、业务日历规则（`CalendarService`）

## 相关文档

- [用户指南](./USER_GUIDE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [决策](./DECISIONS.md)
