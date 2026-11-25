# Discovery — 设计与决策

**模块：** `infra.discovery` · **版本：** `0.2.1`

**最低支持核心版本：** `>=0.5.0`

本文记录本模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

- **收敛横切逻辑**：把「发现带特征的文件 / 类 / 文件夹」的扫描逻辑集中为独立 infra 模块，服务用户自定义功能文件和类，避免各业务复制 `pkgutil` 扫描。
- **语义清晰**：「找子类」与「读模块常量」是两类语义，需要分开表达。
- **健壮装配**：扩展缺失或语法错误不应拖垮装配（fail-soft）。
- **约定优于配置**：鼓励统一的目录与命名约定。

## 方案与思路

- **门面 + 分类发现器**：公开能力一律经 `Discovery.*` 门面；内部拆为 `FileUtils`（单文件操作）、`FileDiscovery`（批量文件发现）、`ClassDiscovery` / `ModuleDiscovery`，不保留模块级便捷函数（见下文 DEC-01 / DEC-02 / DEC-07）。
- **配置对象承载规则**：用 `DiscoveryConfig` 组合过滤、键提取等规则，避免超长 kwargs（见下文 DEC-03）。
- **缓存策略**：`ClassDiscovery` 默认缓存 `DiscoveryResult` 并提供 `clear_cache`；`FileDiscovery` 缓存 key 含 `base_dir` / `pattern` / `file_type` / `max_depth` / `exclude` / `follow_symlinks`；`ModuleDiscovery` 无状态、无缓存（见下文 DEC-04）。
- **fail-soft 与日志级别**：基础包/模块不存在（预期可缺）记 `debug`；单模块导入失败等可继续场景记 `warning` 并跳过；重复注册键不覆盖先发现的类并记 `warning`；其它未捕获异常记 `error`、返回当前结果（见下文 DEC-05）。
- **约定式命名**：`module_name_pattern` 用 `str.format` 占位符 `base_module` / `name`，鼓励统一目录约定（见下文 DEC-06）。

---

## DEC-01：D1：收敛为独立 infra 模块

横切发现逻辑集中，避免各业务复制 `pkgutil` 扫描。

---

## DEC-02：D2：拆分 ClassDiscovery 与 ModuleDiscovery

「找子类」与「读模块常量」语义不同，分类型比单类多分支更清晰。

---

## DEC-03：D3：DiscoveryConfig 承载规则

配置可组合、可测；避免超长 kwargs。

---

## DEC-04：D4：ClassDiscovery 默认缓存

适合启动期多次查询；提供 `clear_cache`；热替换由调用方清理。

---

## DEC-05：D5：fail-soft

扩展缺失或语法错误不拖垮装配；调用方处理空结果。

---

## DEC-06：D6：约定式 module_name_pattern

`str.format` 占位符 `base_module` / `name`，鼓励统一目录约定。

---

## DEC-07：D7：不保留模块级便捷函数与猜测性属性回退

公开能力一律经 `Discovery.*`；已删除 `discover_*` 自由函数、`discover_class_attribute` 约定回退、`discover_modules_by_path`。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
