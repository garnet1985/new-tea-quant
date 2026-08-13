# 文档索引

**主文档与教程请优先访问官网 [new-tea.cn](https://new-tea.cn)。** 以下为仓库内 Markdown，便于离线查阅。

配置约定见模块文档（如 [`project_context`](../core/infra/project_context/README.md)）与 `core/default_config/` JSON；不再在仓库根 `docs/` 单独维护配置专题。

## 用户指南（迁移至 userspace）

- [策略开发](../userspace/strategies/USER_GUIDE.md)
- [数据源使用](../userspace/data_source/USER_GUIDE.md)
- [标签系统](../userspace/tags/USER_GUIDE.md)

## Docker

- [Docker 运行说明](docker.md)（`Dockerfile` / `docker-compose.yml` 在仓库根目录）

## CI

- [ci/README.md](../ci/README.md) — Workflow 专用验收脚本（如冷启动冒烟）；与 `devcli` / `TaskGuard` 分开

## UI（`core/ui/`）

当前仓库内已有 UI 代码骨架：

- `core/ui/fed/`：React 前端（ECharts，可接入 MUI）
- `core/bff/`：Python Flask BFF

## 零散工具

一次性迁移脚本已清理。维护者入口优先 `python devcli.py -h`。

## 架构与设计

- [项目概览](project_overview.md)
- [核心模块标准](../CORE_MODULE_STANDARDS.md)（模块规则：结构 / 测试 / 版本 / Facade 等）
- **文档 SSOT：** [模块文档规范](module-doc-standard.md)（格式 / 放置 / 章节）
- [模块文档模板](doc_templates/module/)（与真实模块同结构；整棵 copy + 填 `<xxx>`）
- 模块文档就近：`core/infra/*`、`core/modules/*` 等各模块根目录 `README.md` / `API.md` 与 `docs/`

## 归档

- 历史根 README 归档已移除（请以仓库根 `README.md` 与模块文档为准）

## 变更记录

- 仓库根目录 [CHANGELOG.md](../CHANGELOG.md)
