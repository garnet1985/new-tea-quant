# System Actions 架构文档

**版本：** `0.2.0`

## 模块介绍

`infra.system_actions` 提供与业务编排解耦的系统级操作：全局 pipeline 租约、模板脚手架。

**核心设计：** Facade `SystemActions`；实现在 `core/pipeline_lease` 与 `core/shortcuts`；包 import 不拉起 strategy/tag（方法内懒导入）。

## 职责与边界

**In scope：** pipeline 租约读写、从模板 scaffold  
**Out of scope：** 回测/打标业务执行、首次安装（见 `infra.setup`）、升级编排（见 `infra.updater`）；临时文件清理（见 `core.infra.cli.dev.scripts.temp_cleanup`）；通用文件发现（见 `infra.discovery`）

## 架构

```text
SystemActions
  ├── pipeline   → core/pipeline_lease.PipelineLease
  ├── scaffold   → core/shortcuts.create_new_*
  └── types      → contracts（含懒加载 PipelineLease）
```

```text
core/infra/system_actions/
├── system_actions.py
├── contracts.py
├── core/
│   ├── pipeline_lease/  # + __test__/
│   └── shortcuts/
└── __test__/            # 公开 API + TEST_CASES.md
```

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
