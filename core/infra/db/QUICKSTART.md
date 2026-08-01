# Database — 快速开始

**模块：** `infra.db` · **版本：** `0.4.0`

最短路径：取得默认 `DatabaseManager` 并查询（需本机已配置数据库）。

---

## 前置条件

- `core/default_config` + `userspace/system/config` 中数据库配置可用
- 公开契约见 [API.md](./API.md)

---

## 最小示例

```python
from core.infra.db import Db
from core.infra.db.contracts import DatabaseManager, DbBaseModel, Field

# 门面
db = Db.manager.get_default()

# 过渡期等价写法
# db = DatabaseManager.get_default()

rows = db.execute_sync_query("SELECT 1 AS n")
print(rows)
```

表模型（示意）::

```python
from core.infra.db.contracts import DbBaseModel, Field

# 真实表定义见 core/tables/**/model.py
```

**预期结果：** 返回一行查询结果（具体视库类型与配置而定）。

---

## 下一步

- [API.md](./API.md)
- [glossary.yaml](./glossary.yaml)
- [README.md](./README.md)

```bash
python3 -m pytest core/infra/db/__test__/test_api.py -q
```
