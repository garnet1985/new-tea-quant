# System Actions 架构文档

**版本：** `0.2.0`

## 模块介绍

`infra.system_actions` 提供与业务编排解耦的系统级操作：缓存清理、全局 pipeline 租约、模板脚手架。

**核心设计：** Facade `SystemActions`；实现在 `core/cache_cleanup` 与 `core/shortcuts`；包 import 不拉起 strategy/tag（方法内懒导入）。

## 职责与边界

**In scope：** 清缓存、pipeline 租约读写、从模板 scaffold  
**Out of scope：** 回测/打标业务执行、升级编排（见 `setup/updater`）；通用文件发现（见 `infra.discovery`）

## 架构

```text
SystemActions
  ├── cache      → core/cache_cleanup.CacheCleanup
  ├── pipeline   → core/cache_cleanup.PipelineLease
  ├── scaffold   → core/shortcuts.create_new_*
  └── types      → contracts（含懒加载 PipelineLease）
```

```text
core/infra/system_actions/
├── system_actions.py
├── contracts.py
├── core/
│   ├── cache_cleanup/   # + __test__/
│   └── shortcuts/
└── __test__/            # 公开 API + TEST_CASES.md
```

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
