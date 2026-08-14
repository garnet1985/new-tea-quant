# Adapter — 快速开始

**模块：** `modules.adapter` · **版本：** `0.2.0`

---

## 最小示例

```python
from core.modules.adapter import Adapter
from core.modules.adapter.contracts import BaseOpportunityAdapter

ok, err = Adapter.validate("console")
print(ok, err)


class MyAdapter(BaseOpportunityAdapter):
    def process(self, opportunities, context):
        ...
```

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/modules/adapter/__test__/test_api.py -q
```
