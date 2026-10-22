---
title: 写扫描后续处理 Adapter
summary: 在 userspace 写 BaseAdapter，用 post_processor.yaml 声明并设 is_enabled。
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

## 2. 声明并启用 PostProcessor

```yaml
# userspace/extensions/post_process/post_processors/my_notify/post_processor.yaml
key: my_notify
is_enabled: true
adapters:
  my_notify:
    config: {}
```

可选 `depends_on: [other_adapter]`；执行时注入 `deps`。  
扫描任意策略结束后会跑所有 ``is_enabled: true`` 的 PostProcessor——不在策略 settings 里挂。

## 检查

1. `PostProcess.validate_adapter("my_notify")`
2. `PostProcess.validate_post_processor("my_notify")`
3. `PostProcess.list_enabled_post_processors()` 应含 `my_notify`
4. 跑一次 `Strategy.scan`
