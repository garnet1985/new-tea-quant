# Discovery — 快速开始

**模块：** `infra.discovery` · **版本：** `0.4.0`

最短路径：用门面 `Discovery` 找文件或扫子类。

---

## 前置条件

- 公开契约见 [API.md](./API.md)

---

## 最小示例

```python
from pathlib import Path
from core.infra.discovery import Discovery

root = Path(".")
path = Discovery.file.find_file(root, "module_info.yaml", search_parents=True)
data = Discovery.file.load_json(path) if path else None
print(path, data)
```

发现子类（将基类与包路径换成你的场景）::

```python
from core.infra.discovery import Discovery

classes = Discovery.discover.subclasses(
    BasePlugin,
    "myproject.plugins",
    module_name_pattern="{base_module}.{name}.plugin",
    key_extractor=lambda cls: getattr(cls, "plugin_name", None),
)
```

**预期结果：** 返回文件路径 / 配置 dict，或 `{key: class}` 映射。

---

## 下一步

- [API.md](./API.md)
- [README.md](./README.md)

```bash
python3 -m pytest core/infra/discovery/__test__/test_api.py -q
```
