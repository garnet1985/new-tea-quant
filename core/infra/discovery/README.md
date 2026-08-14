# Discovery（`infra.discovery`）

为 New Tea Quant（简称 **NTQ**）提供可配置的文件与类发现能力：单文件读写、批量路径扫描、按基类枚举子类、按模块名收集对象。对外门面类（Facade）为 `Discovery`。词条见 [glossary.yaml](./glossary.yaml)。

## 适用场景

- 在 userspace / core 扩展目录中枚举 Provider、Handler、Strategy 等插件类。
- 查找并加载 JSON / YAML / Python 配置文件。
- 按约定路径批量收集模块级常量（如 `SCHEMA`）。

## 模块依赖

无（标准库为主）。调用方若用路径辅助定位根目录，自行依赖 `project_context` 等。

## 设计初衷

- **要解决的问题：** 用统一入口替代各业务模块手写 `pkgutil` / `importlib` 扫描。
- **明确不做：** 不定义业务基类；不做热更新 / 文件监视 / 跨进程缓存。

## 常见问题

**Q：代码里该 import 什么？**  
A：`from core.infra.discovery import Discovery`；类型见 `contracts`。见 [API.md](./API.md)。

**Q：实现在哪？**  
A：`core/` 子包；勿将内部类当作公开 import 面。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
