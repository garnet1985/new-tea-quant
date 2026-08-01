# 文档索引

**主文档与教程请优先访问官网 [new-tea.cn](https://new-tea.cn)。** 以下为仓库内 Markdown，便于离线查阅。

## 配置文档（仓库内）

- [默认配置总览](default_config/overview.md)
- [默认配置架构](default_config/architecture.md)
- [默认配置决策](default_config/decisions.md)
- [默认配置用户指南](default_config/user_guide.md)

## 用户指南（迁移至 userspace）

- [策略开发](../userspace/strategies/USER_GUIDE.md)
- [数据源使用](../userspace/data_source/USER_GUIDE.md)
- [标签系统](../userspace/tags/USER_GUIDE.md)

## 仓库辅助工具（devtools）

面向维护者与本地开发：**不参与**运行时业务逻辑。结构与入口如下（路径均相对仓库根目录）。

| 路径 | 说明 |
|------|------|
| [devtools/docker/README.md](../devtools/docker/README.md) | Docker Compose 用法；**`Dockerfile`**、**`docker-compose.yml`** 仍在仓库根目录 |
| `devtools/automation/badge_updating/update_readme_version_badge.py` | 将根目录 `README.md` 中版本徽章与 `core/system.json` 对齐 |
| `devtools/automation/table_exporting/export_table.py` | 基于 `model.export_data` 的按表导出 CLI（维护/Demo 用） |

## UI（`core/ui/`）

当前仓库内已有 UI 代码骨架：

- `core/ui/fed/`：React 前端（ECharts，可接入 MUI）
- `core/bff/`：Python Flask BFF

## 零散工具（`tools/`）

与 `devtools` 区分：偏**数据比对、一次性迁移、演示导出**等，见 [tools/README.md](../tools/README.md)。

## 架构与设计

- [项目概览](project_overview.md)
- [核心模块标准](../CORE_MODULE_STANDARDS.md)（模块规则：结构 / 测试 / 版本 / Facade 等）
- **文档 SSOT：** [模块文档规范](module-doc-standard.md)（格式 / 放置 / 章节）
- [模块文档模板](doc_templates/module/)（与真实模块同结构；整棵 copy + 填 `<xxx>`）

## 变更记录

- 仓库根目录 [CHANGELOG.md](../CHANGELOG.md)
