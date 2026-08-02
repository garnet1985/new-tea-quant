# 命令行布局（`infra.cmd_layout`）

为 New Tea Quant（简称 **NTQ**）的命令行（CLI）报告提供**纯文本排版助手**：标题、分割线、跨平台图标、水平条形图 / 直方图。对外只暴露门面类（Facade）`CmdLayout`。词条见 [glossary.yaml](./glossary.yaml)。

## 适用场景

- 策略报告 `present` 等需要在终端打印整齐的标题区、分隔与简易分布图。
- 安装 / 开发工具需要按终端能力输出 emoji 或 ASCII 图标。
- 希望 Windows / Linux / macOS 终端默认不因特殊 Unicode 条形字符乱码。

## 模块依赖

无（`module_info.yaml` 的 `dependencies` 为空）。

## 设计初衷

- **要解决的问题：** 把报告排版常用片段收成统一入口，并保证跨平台终端可读。
- **明确不做：** 不做 GUI 图表；不把内部 `Title` / `BarChart` / `IconService` 等当作跨模块公开 import 面。

## 常见问题

**Q：该 import 什么？**  
A：只 `from core.infra.cmd_layout import CmdLayout`，见 [API.md](./API.md)。

**Q：条形图为什么用 `#` 而不是方块字符？**  
A：避免 Windows GBK 等环境乱码，见 [docs/DESIGN.md](./docs/DESIGN.md)。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
