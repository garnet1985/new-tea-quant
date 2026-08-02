# Utils（`infra.utils`）

与业务无关的通用工具：日期、类型/DataFrame、CSV/归档 IO、确定性随机。

## 布局

```text
core/infra/utils/
├── utils.py            # Facade Utils
├── type_utils.py       # Utils.types 实现
├── contracts.py
├── date/ / io/ / math/ # 内部实现
├── API.md / QUICKSTART.md / glossary.yaml
├── __test__/
└── docs/
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.utils import Utils

Utils.date.today()
Utils.io.write_dicts_to_csv(path, rows)
```

配置合并请用 `ProjectContext.config` / `ConfigManager`，不要用本模块替代。

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
