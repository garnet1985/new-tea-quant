# Update — 快速开始

**模块：** `infra.update` · **版本：** `0.5.0`

最短路径：注册并运行一条 post-upgrade 动作（注册表为空则跳过）。

---

## 最小示例

```python
from pathlib import Path
from core.infra.update import Update

result = Update.post_upgrade.run(Path("."))
print(result.skipped, result.executed_count)
```

**预期结果：** 无注册动作时 `skipped=True`。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/update/__test__/test_api.py -q
```
