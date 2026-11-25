# 扫描后续处理（PostProcess）

扫描结束后，框架把机会规范成协议，再跑 userspace 里所有 **`is_enabled: true`** 的 **PostProcessor**（各含一组 **Adapter**）。与策略 settings 无关。

## 目录

```text
userspace/extensions/post_process/
├── adapters/<name>/adapter.py
└── post_processors/<key>/post_processor.json   # is_enabled: true|false
```

## 启用

```json
{
  "key": "presenter",
  "is_enabled": true
}
```

详见 `core/modules/post_process/docs/`。
