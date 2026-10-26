# infra.discovery — 决定

**版本：** `0.2.1`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

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


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
