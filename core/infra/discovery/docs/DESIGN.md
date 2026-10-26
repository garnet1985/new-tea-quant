# Discovery 详细设计

**版本：** `0.2.1`

实现向细节；鸟瞰与边界见 [ARCHITECTURE.md](./ARCHITECTURE.md)。公开入口见根目录 [API.md](../API.md)。

---

## 1. 组件关系

```text
Discovery（门面）
  ├── file → FileUtils
  ├── discover → FileDiscovery / ClassDiscovery / ModuleDiscovery
  └── class_discovery → DiscoveryConfig + ClassDiscovery

DiscoveryConfig ──► ClassDiscovery ──► DiscoveryResult
```

---

## 2. `ClassDiscovery.discover` 扫描语义

1. `importlib.import_module(base_module_path)` 得到基础包；取其 `__path__`。
2. `pkgutil.iter_modules` 得到一级子项；**仅当 `ispkg` 为真**且不在 `skip_modules`、不以 `_` 开头时继续。
3. `module_path = module_name_pattern.format(base_module=..., name=modname)`。
4. 导入后筛 `issubclass(..., base_class)`，经 `class_filter` / `key_extractor`。
5. 键冲突：**不覆盖**先发现的类，打 `warning`。
6. `use_cache` 时按 `base_module_path` 缓存 `DiscoveryResult`。

基础包 `ImportError`：debug，返回空结果。其它未捕获异常：error，返回当前结果。

---

## 3. `ModuleDiscovery.discover_objects` 扫描语义

1. 导入基础包，遍历一级子模块名（**不**要求 `ispkg`）。
2. 按 `module_pattern` 导入；存在 `object_name` 则收集。
3. 单模块失败跳过（fail-soft）。

---

## 4. 定点加载

- `ClassDiscovery.discover_class_by_path`（staticmethod）：`class_path.rsplit('.', 1)` → import → `getattr`；可选 `issubclass`。

---

## 4b. `find_in_tree`（按目录名 key）

与 `find_file`（任意深度同名文件）不同：目标路径形如 `**/{key}/{filename}`。

1. 校验 `key` / `filename` 为单路径段。
2. 先试 `base_dir / key / filename`。
3. 再 `base_dir.rglob(f"{key}/{filename}")`，取排序后首个文件。

自 `project_context.DiscoveryManager.find_in_tree` 迁入；业务（如 data_source handlers）经 `Discovery.file.find_in_tree` 调用。

---

## 5. 缓存与并发

- `ClassDiscovery` 实例内 `_cache`；无锁，假定串行初始化。
- `FileDiscovery` 缓存 key 含 `base_dir` / `pattern` / `file_type` / `max_depth` / `exclude` / `follow_symlinks`。
- `ModuleDiscovery` 无状态、无缓存。

---

## 6. 日志级别约定

| 场景 | 级别 |
|------|------|
| 基础包/模块不存在（预期可缺） | `debug` |
| 单模块导入失败等可继续 | `warning` |
| 重复注册键 | `warning` |

---

## 附录：设计决策（原 DECISIONS）

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）