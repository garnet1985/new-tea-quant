# modules.data_manager — 决定

**版本：** `0.2.3`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：决策 1：Facade 与单例

**决策：** 默认进程内单例（锁 + 双重检查）；`force_new` 用于测试/隔离。  
**影响：** 多进程每进程各自 `DataManager`。

---

## DEC-02：决策 2：表定义在 `core/tables` 与 `userspace/extensions/tables`

**决策：** 递归发现 `schema.py`；core 强制 `sys_` 前缀。

---

## DEC-03：决策 3：领域服务属性链

**决策：** 经 `stock` / `macro` / `calendar` / … 属性访问，不包根导出各 Service 类。

---

## DEC-04：决策 4：样本股票宇宙属于 DataManager

**决策：** `use_sample_stock_list` 决定系统内保留哪些股票，经 `DataManager.sample_universe` 访问。data_source 只消费该宇宙（抓取切片 / 写库过滤），不持有名单文件或 API。

---


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
