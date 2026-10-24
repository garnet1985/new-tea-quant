# PostProcess（`modules.post_process`）

策略 **Scanner** 完成后，将机会规范为三层出口协议，再执行 userspace 中所有 **`is_enabled: true`** 的 **PostProcessor**（各含一组 Adapter）。

后续处理是**全局**配置，不在策略 `settings.scanner` 里。

## 布局

```text
core/modules/post_process/
├── post_process.py     # Facade PostProcess
├── contracts.py        # 协议 + BaseAdapter
├── core/
├── API.md / QUICKSTART.md / glossary.yaml
└── docs/
```

## userspace

```text
userspace/extensions/post_process/
├── adapters/<name>/adapter.py
└── post_processors/<key>/post_processor.yaml   # 含 is_enabled
```

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.post_process import PostProcess`；契约 `from core.modules.post_process.contracts import BaseAdapter, ScanSessionReport, ...`。

**Q：怎么启用 / 关闭？**  
A：改 `post_processors/<key>/post_processor.yaml` 的 `is_enabled`。扫描任意策略结束后会跑所有 enabled 的 PostProcessor。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
- [出口协议](./docs/PROTOCOL.md)
- [PostProcessor](./docs/POST_PROCESSOR.md)
