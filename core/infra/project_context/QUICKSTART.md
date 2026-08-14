# Project Context — 快速开始

**模块：** `infra.project_context` · **版本：** `0.2.0`

最短路径：取根路径并加载一份配置。

---

## 最小示例

```python
from core.infra.project_context import ProjectContext

root = ProjectContext.path.get_project_root()
settings = ProjectContext.config.load_core_config("logging")
print(root, settings.get("level"))
```

**预期结果：** 得到绝对项目根路径，以及合并后的 logging 配置字典。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/project_context/__test__/test_api.py -q
```
