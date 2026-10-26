# 命令行布局（`infra.cmd_layout`）

**模块：** `infra.cmd_layout` · **版本：** `0.2.0`

## 简介

终端排版工具箱。在 CLI 里打印标题、分割线、表格、水平条形图、图标——跨平台兼容，Windows 不会乱码。对外走 `CmdLayout` 门面。

## 适用场景

- 策略报告打印整齐的标题区和对照表
- 安装流程需要终端图标（macOS 显示 emoji，Windows 自动降级成 ASCII）
- 想在终端画简易条形图，不想自己算字符宽度

## 模块依赖

无硬依赖

## 设计初衷

- **要解决的问题：** 把报告排版常用片段收成统一入口，每个模块不再自己画 ASCII 艺术。
- **明确不做：** 不做 GUI 图表；内部 `Title` / `BarChart` / `IconService` 等实现类不对外部暴露。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [快速开始](./QUICKSTART.md)
- [决策](./docs/DECISIONS.md)
