# 扫描后续处理（PostProcess）

扫描结束后，框架把机会规范成协议，再按策略配置的 **PostProcessor** 跑一组 **Adapter**。

## 目录

```text
userspace/extensions/post_process/
├── adapters/<name>/adapter.py
└── post_processors/<key>/post_processor.yaml
```

## 策略配置

```python
"scanner": {
    "post_process": "console",
}
```

详见 `core/modules/post_process/docs/`。
