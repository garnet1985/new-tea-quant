# Project Context（`infra.project_context`）

项目根推断、语义路径、约定式配置发现与默认/用户配置合并。

## 适用场景

- 解析 `userspace`、策略 / Tag / data_source 目录
- 合并 `core/default_config` 与 `userspace/config`
- 统一通过 Facade：`ProjectContext.path` / `.config` / `.discovery` / `.meta` / `.cache`

## 布局

```text
core/infra/project_context/
├── module_info.yaml
├── API.md / QUICKSTART.md / glossary.yaml / contracts.py
├── project_context.py          # Facade
├── core/                       # 内部实现
├── __test__/
└── docs/
    ├── ARCHITECTURE.md
    └── DESIGN.md
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.project_context import ProjectContext

root = ProjectContext.path.get_project_root()
data_cfg = ProjectContext.config.load_data_config()
```

```bash
python3 -m pytest core/infra/project_context/__test__/test_api.py -q
```

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- [docs/DESIGN.md](./docs/DESIGN.md)
