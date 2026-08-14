# Strategy — 快速开始

**模块：** `modules.strategy` · **版本：** `0.6.0`

## 最小示例

```python
from core.modules.strategy import Strategy

names = Strategy.list_strategies()
print(names[:3])
```

## 枚举一步

```python
result = Strategy.enumerate("demo/random/random_v1_null_baseline")
print(result.get("total_opportunities"))
```

```bash
python3 -m pytest core/modules/strategy/__test__/test_api.py -q
```
