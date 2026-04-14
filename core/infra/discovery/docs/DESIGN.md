# Discovery 详细设计

**版本：** `0.2.0`

本文档说明 `infra.discovery` 的实现向细节；鸟瞰与边界见 [架构总览](./ARCHITECTURE.md)。

**相关文档**：[架构总览](./ARCHITECTURE.md) · [API](./API.md) · [决策记录](./DECISIONS.md)

---

## 1. 组件关系

```text
DiscoveryConfig ──► ClassDiscovery ──► DiscoveryResult
 │
 ├── discover                         ├── discover_class_by_path
                         ├── discover_class_attribute
                         └── clear_cache

ModuleDiscovery (静态方法)
    ├── discover_objects
    └── discover_modules_by_path

discover_subclasses(...) ──► ClassDiscovery + DiscoveryConfig薄封装
```

---

## 2. `ClassDiscovery.discover` 扫描语义

1. `importlib.import_module(base_module_path)` 得到基础包；取其 `__path__`。
2. `pkgutil.iter_modules(package_paths)` 得到一级子项 `(importer, modname, ispkg)`。
3. **仅当 `ispkg` 为真**且 `modname` 不在 `skip_modules`、不以 `_` 开头时继续。
4. `module_path = module_name_pattern.format(base_module=base_module_path, name=modname)`。
5. 导入 `module_path` 后，对 `dir(module)` 中每个 `type` 且 `issubclass(attr, base_class)`、排除基类自身、通过 `class_filter`（若有）的类：
   - `key = key_extractor(cls)`，若配置存在且 `key` 为假值则跳过；
   - 无 `key_extractor` 时用类名字符串。
6. 写入 `result.classes[key]`；若键已存在则 **不覆盖**，打 `warning`。
7. 对每个 `attribute_extractors` 条目，将 `extractor(cls)` 记入 `result.metadata[attr_name][key]`。
8. `use_cache` 为真时将 `result` 存入 `_cache[base_module_path]`。

基础包 `ImportError`：debug 日志，返回空结果。其它未捕获异常：error 日志，返回当前 `result`。

---

## 3. `ModuleDiscovery.discover_objects` 扫描语义

1. 导入 `base_module_path`，遍历 `pkgutil.iter_modules`。
2. **不**检查 `ispkg`：一级子模块名无论包或单文件均可。
3. `module_path = module_pattern.format(base_module=base_module_path, name=modname)`。
4. 导入成功后若存在 `object_name` 属性则 `objects[modname] = getattr(...)`；否则 debug 无该属性。
5. `ImportError` 跳过；其它异常 warning。基础包不存在：debug，返回 `{}`。

---

## 4. `discover_modules_by_path`

1. `base_path` 不存在则返回 `{}`。
2. `iterdir()` 中仅处理目录、且目录名不以 `_` 开头。
3. `module_path = module_pattern.format(name=item.name)`（**仅** `name` 占位符，与 `discover_objects` 不同）。
4. 导入模块；若给定 `object_name` 则收集对象，否则收集模块本身。

---

## 5. 定点加载与属性回退

### `discover_class_by_path`

- `class_path.rsplit('.', 1)` 得到 `(module_path, class_name)`。
- `getattr(module, class_name)`；可选 `issubclass` 校验，`TypeError` 时放弃校验（与实现一致）。

### `discover_class_attribute`

1. 先用 `discover_class_by_path(..., base_class=None)` 取类；若类上存在非空 `attribute_name` 则返回。
2. 否则在同一模块上查找属性名为 `class_name + attribute_name.capitalize()` 的对象。  
   Python的 `str.capitalize()` 只将首字符大写、其余小写，因此 `attribute_name="config_class"` 时后缀为 `Config_class`，而非驼峰式的 `ConfigClass`。

---

## 6. 缓存与并发

- 缓存粒度：`ClassDiscovery` 实例内 `_cache`，键为 `base_module_path` 字符串。
- 无锁；假定单线程初始化或调用方串行。多线程并发 `discover` 需调用方外部同步。
- `ModuleDiscovery` 无状态、无缓存。

---

## 7. 日志级别约定（实现现状）

| 场景 | 级别 |
|------|------|
| 基础包/模块不存在（预期可缺） | `debug` |
| 单模块导入失败、属性缺失等可继续 | `warning`（`discover` 外层未捕获用 `error`） |
| 重复注册键 | `warning` |

---

## 8. 与测试的依赖

单元测试可能引用 `userspace.*` 与 `core.infra.project_context.PathManager`；本模块实现本身不依赖 `project_context`。
