# PostProcess（`modules.post_process`）

**模块：** `modules.post_process` · **版本：** `0.3.0`

策略 Scanner 完成后，将机会规范为三层出口协议（`Opportunity` → `StrategyScanReport` → `ScanSessionReport`），再执行 userspace 中所有 **`is_enabled: true`** 的 PostProcessor（各含一组 Adapter）。后续处理是**全局**配置，不在策略 `settings.scanner` 里。

## 适用场景

- 扫描出机会后，需要通知微信 / 邮件 / 企微、或对接本地 Broker 做模拟下单等分发处理
- 想让各 Adapter 彼此协作（一个 Adapter 的产出作为另一个的依赖）

## 模块依赖

- `infra.project_context`
## 设计初衷

- **要解决的问题：** 扫描结果的"出口分发"不应写死在 Strategy 里。Strategy 只管产机会，PostProcess 管怎么分发。
- **明确不做：** 不做"流水线"语义（Adapter 是无序集合，非 pipeline）；不做依赖图以外的业务逻辑。

## 常见问题

**Q：该 import 什么？**
A：`from core.modules.post_process import PostProcess`；契约与 `BaseAdapter` 从 `contracts` 导入。

**Q：怎么启用 / 关闭？**
A：改 `userspace/extensions/post_process/post_processors/<key>/post_processor.yaml` 的 `is_enabled`。

## 相关文档

- [公开 API](./API.md)
- [快速开始](./QUICKSTART.md)
- [架构](./docs/ARCHITECTURE.md)
- [出口协议](./docs/PROTOCOL.md)
- [PostProcessor](./docs/POST_PROCESSOR.md)
