# Discovery API 文档

**版本：** `0.4.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Discovery`；类型从 [`contracts.py`](./contracts.py) 导入。实现位于 [`core/`](./core/)。

---

## Discovery

**描述：** 发现门面类（Facade）— `file` / `discover` / `class_discovery` 命名空间

### file

**描述：** 单文件查找与读写（JSON / YAML / 文本 / Python 配置）

#### find_file

`Discovery.file.find_file(start_dir, filename, *, search_parents=False, max_depth=10) -> Path | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 自 `start_dir` 查找文件名；可选向上搜索父目录
- **举例：**

```python
from pathlib import Path
from core.infra.discovery import Discovery

p = Discovery.file.find_file(Path("."), "settings.json", search_parents=True)
```

#### load_json / load_yaml / load_text

`Discovery.file.load_json(path) -> dict | None`  
`Discovery.file.load_yaml(path) -> dict | None`  
`Discovery.file.load_text(path, *, encoding="utf-8") -> str | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 按格式加载；JSON/文本失败返回 `None`；YAML 需已安装 `pyyaml`，缺失则抛 `RuntimeError`

#### load_file_content

`Discovery.file.load_file_content(path, *, encoding="utf-8", auto_detect_format=True) -> str | dict | bytes | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 加载文件；可按后缀自动识别 JSON/YAML/文本

#### load_python_config

`Discovery.file.load_python_config(path, var_name="settings") -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 对**受信** Python 配置文件 `exec` 后提取指定变量（须为 mapping）；勿用于不可信输入

#### save_file_content / save_json / save_yaml

`Discovery.file.save_file_content(path, content, *, encoding="utf-8", ensure_parent_exists=True) -> bool`  
`Discovery.file.save_json(path, data, *, encoding="utf-8") -> bool`  
`Discovery.file.save_yaml(path, data, *, encoding="utf-8") -> bool`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 写入文件；成功返回 `True`；YAML 需 `pyyaml`

---

### discover

**描述：** 批量路径发现与包内子类 / 对象发现

#### files / directories / files_by_suffix

`Discovery.discover.files(base_dir, pattern="**/*", *, exclude_patterns=None, max_depth=10) -> list[Path]`  
`Discovery.discover.directories(base_dir, pattern="**/*", *, exclude_patterns=None, max_depth=10) -> list[Path]`  
`Discovery.discover.files_by_suffix(base_dir, suffix, *, exclude_patterns=None, max_depth=10) -> list[Path]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 在目录树中批量发现文件或目录；`files_by_suffix` 的 `suffix` 须含点（如 `.json`）

#### subclasses

`Discovery.discover.subclasses(base_class, base_module_path, module_name_pattern="{base_module}.{name}", key_extractor=None, class_filter=None) -> dict[str, Type]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 在基础包下按模式发现 `base_class` 的子类，返回 `{key: class}`

#### objects

`Discovery.discover.objects(base_module_path, object_name, module_pattern="{base_module}.{name}", skip_modules=None) -> dict[str, Any]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 在一级子模块中收集同名模块属性

---

### class_discovery

**描述：** 高级类发现（配置对象 + 定点路径加载）

#### create_config

`Discovery.class_discovery.create_config(base_class, module_name_pattern, ...) -> DiscoveryConfig`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 构造 `DiscoveryConfig`（见 contracts）

#### create

`Discovery.class_discovery.create(config: DiscoveryConfig) -> ClassDiscovery`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 构造可缓存的 `ClassDiscovery` 实例（`discover` / `clear_cache` 等）

#### discover_class_by_path

`Discovery.class_discovery.discover_class_by_path(class_path, base_class=None) -> Type | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 按全限定名加载单个类，可选基类校验

---

## contracts（`core.infra.discovery.contracts`）

| 符号 | 说明 | 状态 |
|------|------|------|
| `DiscoveryConfig` | 类发现规则 | `beta` |
| `DiscoveryResult` | `classes` + `metadata` | `beta` |
| `ClassDiscovery` | 可缓存类发现器 | `beta` |
| `FileDiscoveryConfig` | 文件批量发现配置 | `beta` |
