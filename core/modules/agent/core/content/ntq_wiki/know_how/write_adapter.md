---
title: 写扫描后续处理 Adapter
summary: 在 userspace 写 BaseAdapter，并用 post_processor YAML 挂到策略 scanner.post_process。
---

# 写扫描后续处理 Adapter

## 1. 创建 adapter

```text
userspace/extensions/post_process/adapters/my_notify/
├── adapter.py
└── settings.py   # 可选
```

```python
from typing import Any, Dict
from core.modules.post_process.contracts import BaseAdapter, ScanSessionReport


class MyNotifyAdapter(BaseAdapter):
    def run(
        self,
        session: ScanSessionReport,
        config: Dict[str, Any],
        deps: Dict[str, Any],
    ) -> None:
        for report in session.strategies:
            print(report.strategy_name, len(report.opportunities))
```

## 2. 声明 PostProcessor

```yaml
# userspace/extensions/post_process/post_processors/my_notify/post_processor.yaml
key: my_notify
adapters:
  my_notify:
    config: {}
```

可选 `depends_on: [other_adapter]`；执行时注入 `deps`。

## 3. 策略挂上

```python
"scanner": {
    "post_process": "my_notify",
}
```

## 检查

1. `PostProcess.validate_adapter("my_notify")`
2. `PostProcess.validate_post_processor("my_notify")`
3. 跑一次 `Strategy.scan`
