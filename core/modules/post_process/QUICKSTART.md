# PostProcess 快速开始

## 写一个 Adapter

```python
# userspace/extensions/post_process/adapters/my_notify/adapter.py
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

## 声明 PostProcessor

```yaml
# userspace/extensions/post_process/post_processors/my_notify/post_processor.yaml
key: my_notify
adapters:
  my_notify:
    config: {}
```

## 策略挂上

```python
"scanner": {
    "post_process": "my_notify",
}
```

## 门面

```python
from core.modules.post_process import PostProcess

session = PostProcess.build_session_report(
    scan_date="20240110",
    strategy_name="demo",
    opportunities=[],
)
PostProcess.run_post_processor("console", session)
```
