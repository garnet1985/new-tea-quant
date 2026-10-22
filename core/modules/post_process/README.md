# PostProcess（`modules.post_process`）

策略 **Scanner** 完成后，将机会规范为三层出口协议，再按 `scanner.post_process` 执行 userspace **PostProcessor**（一组独立 Adapter）。

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
└── post_processors/<key>/post_processor.yaml
```

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.post_process import PostProcess`；契约 `from core.modules.post_process.contracts import BaseAdapter, ScanSessionReport, ...`。

**Q：策略怎么挂？**  
A：`settings.scanner.post_process = "console"`。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [出口协议](./docs/PROTOCOL.md)
- [PostProcessor](./docs/POST_PROCESSOR.md)
