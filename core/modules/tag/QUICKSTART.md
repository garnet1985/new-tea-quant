# Tag — 快速开始

**模块：** `modules.tag` · **版本：** `0.4.0`

## 最小示例

```python
from core.modules.tag import Tag

Tag().execute(scenario_name="demo/market_cap_tier")
```

**预期结果：** 对已启用场景执行 tag 计算并落库（非 dry_run）。

## 下一步

- [API.md](./API.md)
- userspace 场景：`userspace/extensions/tags/<path>/settings.py` + `tag.py`

```bash
python3 -m pytest core/modules/tag/__test__/test_api.py -q
```
