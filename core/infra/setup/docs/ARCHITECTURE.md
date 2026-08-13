# Setup 架构文档

**版本：** `0.1.0`

## 模块介绍

`infra.setup` 是安装域：判断是否需要安装、跑步骤流水线、生产 `initialization/userspace` / `initialization/data` 产物、UI/CLI 安装编排。

**核心设计：** setup 全权管理安装；CLI 只调用 `Setup` 门面。冷启动（`install.py` / `launcher.py` / Docker zip）不依赖 argparse CLI。

## 职责与边界

**In scope：** venv、依赖、userspace 初始化、演示数据导入/导出、安装状态、产物 zip 的**生产逻辑**  
**Out of scope：** 应用升级（见 `infra.updater`）；zip 落盘目录（`initialization/userspace/`、`initialization/data/`）；用户策略/打标命令

## 架构

```text
core/infra/setup/         # 执行层
  setup.py / contracts.py
  core/{env, install_runtime, cli_runtime, ui_runtime, steps, scripts}

initialization/userspace/ initialization/data/   # 仓库根产物
```

```text
Setup
  ├── env        → core.env.NewTeaQuantSetup + 路径常量
  ├── runtime    → core.install_runtime / cli_runtime / ui_runtime
  ├── artifacts  → core.scripts.init_userspace / init_data
  ├── meta       → core.meta_loader
  ├── trace      → core.trace_events.SetupTrace
  └── types      → contracts
```

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
