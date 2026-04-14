# Discovery 模块（`infra.discovery`）

按约定路径扫描 Python 包，加载继承指定基类的子类、模块内命名对象（如 `SCHEMA`），以及通过路径解析类与其关联属性。

## 适用场景

- 在 userspace 或 core 扩展目录中枚举 Provider、Handler、Worker、Adapter 等插件类。
- 从各 handler 子包中收集模块级常量或 Schema对象。
- 根据类的全名解析其实现，并按约定名在模块中寻找配对类型（如 Handler 与 Config）。

## 快速定位

```text
core/infra/discovery/
├── module_info.yaml
├── __init__.py
├── class_discovery.py
├── module_discovery.py
├── __test__/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 快速开始

以下示例仅说明调用形态；请将 `BasePlugin` 与包路径换成你项目中的基类与包名。

```python
from core.infra.discovery import ClassDiscovery, DiscoveryConfig, ModuleDiscovery

# 1) 枚举某包下符合基类与过滤条件的子类
config = DiscoveryConfig(
    base_class=BasePlugin,
    module_name_pattern="{base_module}.{name}.plugin",
    key_extractor=lambda cls: getattr(cls, "plugin_name", None) or None,
    class_filter=lambda cls: bool(getattr(cls, "plugin_name", None)),
)
result = ClassDiscovery(config).discover("myproject.plugins")

# 2) 枚举子包模块中的同名对象
schemas = ModuleDiscovery().discover_objects(
    base_module_path="myproject.handlers",
    object_name="SCHEMA",
    module_pattern="{base_module}.{name}.schema",
)
```

运行本模块单元测试（在仓库根目录）：

```bash
python3 -m pytest core/infra/discovery/__test__/ -q
```

## 模块依赖

无（仅使用标准库：`importlib`、`pkgutil`、`inspect` 等）。调用方若配合 `PathManager` 等使用 `discover_modules_by_path`，由调用方负责引入对应模块。

## 当前实现说明（代码对齐）

- `ClassDiscovery.discover` 只遍历基础包下的**子包**（`pkgutil.iter_modules` 且 `ispkg` 为真）；单层 `.py` 子模块不会被当作发现入口。
- `ModuleDiscovery.discover_objects` 遍历基础包下**一级**子模块名，按 `module_pattern` 拼接后导入；缺对象或导入失败则跳过并打日志。
- `ClassDiscovery` 按 `base_module_path` 缓存 `DiscoveryResult`；`ModuleDiscovery` 无缓存。
- 单个子类注册键冲突时保留先发现的类，并输出 warning。

## 相关文档

- `docs/ARCHITECTURE.md`
- `docs/DESIGN.md`
- `docs/API.md`
- `docs/DECISIONS.md`
