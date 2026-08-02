# Discovery 详细设计

**版本：** `0.4.0`

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

## 4. `discover_modules_by_path`

基于文件系统目录名映射为模块路径（占位符主要是 `name`）；实现细节见 `module_discovery.py`。

---

## 5. 定点加载与属性回退

- `discover_class_by_path`：`class_path.rsplit('.', 1)` → import → `getattr`；可选 `issubclass`。
- `discover_class_attribute`：先读类属性；否则模块上查找 `类名 + attribute_name.capitalize()`（注意 `capitalize` 语义）。

---

## 6. 缓存与并发

- `ClassDiscovery` 实例内 `_cache`；无锁，假定串行初始化。
- `ModuleDiscovery` 无状态、无缓存。

---

## 7. 日志级别约定

| 场景 | 级别 |
|------|------|
| 基础包/模块不存在（预期可缺） | `debug` |
| 单模块导入失败等可继续 | `warning` |
| 重复注册键 | `warning` |

---

## 附录：设计决策（原 DECISIONS）

### D1：收敛为独立 infra 模块

横切发现逻辑集中，避免各业务复制 `pkgutil` 扫描。

### D2：拆分 ClassDiscovery 与 ModuleDiscovery

「找子类」与「读模块常量」语义不同，分类型比单类多分支更清晰。

### D3：DiscoveryConfig 承载规则

配置可组合、可测；避免超长 kwargs。

### D4：ClassDiscovery 默认缓存

适合启动期多次查询；提供 `clear_cache`；热替换由调用方清理。

### D5：fail-soft

扩展缺失或语法错误不拖垮装配；调用方处理空结果。

### D6：约定式 module_name_pattern

`str.format` 占位符 `base_module` / `name`，鼓励统一目录约定。
