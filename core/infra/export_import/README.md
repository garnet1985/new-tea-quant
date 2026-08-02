# Export / Import（`infra.export_import`）

为 New Tea Quant（简称 **NTQ**）提供 userspace 制品**打包与安装**公用能力：目录收集、zip 归档、`manifest.json`、冲突预检与按策略落盘。对外门面类（Facade）为 `ExportImport`。词条见 [glossary.yaml](./glossary.yaml)。

## 适用场景

- 策略包 / 扩展包导出为 zip、再安装到另一环境的 userspace
- 安装前按 `reject` / `skip_existing` / `overwrite` 做冲突预检

## 模块依赖

无硬性模块依赖（路径由调用方传入）。

## 设计初衷

- **要解决的问题：** 把打包 / 落盘从具体业务编排中抽离，避免 strategy 等模块重复实现 zip 与冲突逻辑。
- **明确不做：** 不解析业务依赖图（tag / adapter）；不负责导入后的 discovery / validate。

## 常见问题

**Q：该 import 什么？**  
A：`from core.infra.export_import import ExportImport`；类型用 `ExportImport.types` 或 `contracts`。见 [API.md](./API.md)。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
