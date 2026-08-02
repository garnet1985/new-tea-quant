# System Actions 架构文档

**版本：** `0.2.0`

## 模块介绍

`infra.system_actions` 提供与业务编排解耦的系统级操作：缓存清理、全局 pipeline 租约、模板脚手架。

**核心设计：** Facade `SystemActions`；实现分 `cache_cleanup/` 与 `shortcuts/`；包 import 不拉起 strategy/tag（方法内懒导入）。

## 职责与边界

**In scope：** 清缓存、pipeline 租约读写、从模板 scaffold  
**Out of scope：** 回测/打标业务执行、升级编排（见 `setup/updater` / `infra.update`）

## 架构

```text
SystemActions
  ├── cache      → cache_cleanup.cache_cleanup
  ├── pipeline   → cache_cleanup.pipeline_lease
  └── scaffold   → shortcuts.create_new_*
contracts        → Scaffold* / PipelineLeaseBusyError / VALID_KINDS
```

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
