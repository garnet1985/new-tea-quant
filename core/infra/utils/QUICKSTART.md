# Utils — 快速开始

**模块：** `infra.utils` · **版本：** `0.2.0`

最短路径：规范化日期并算日差。

---

## 最小示例

```python
from core.infra.utils import Utils

d = Utils.date.normalize_str("2024-01-15")
print(d, Utils.date.diff_days(d, "20240120"))
```

**预期结果：** `20240115` 与 `5`。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/utils/__test__/test_api.py -q
```
