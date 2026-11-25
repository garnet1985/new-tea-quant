# PostProcess 快速开始

**模块：** `modules.post_process` · **版本：** `0.3.2`

**最低支持核心版本：** `>=0.5.0`

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

```json
{
  "key": "my_notify",
  "is_enabled": true,
  "adapters": {
    "my_notify": {
      "config": {}
    }
  }
}
```

启用是全局的：每个策略扫描结束后会跑全部 `is_enabled: true` 的方案。也可在工作台「高级功能 → 后续处理」里开关启用、编辑 adapters / `depends_on`。

## 门面

```python
from core.modules.post_process import PostProcess

session = PostProcess.build_session_report(
    scan_date="20240110",
    strategy_name="demo",
    opportunities=[],
)
PostProcess.run_enabled_post_processors(session)
# 或显式：PostProcess.run_post_processor("presenter", session)
```
