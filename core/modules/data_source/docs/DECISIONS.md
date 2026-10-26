# modules.data_source — 决定

**版本：** `0.4.0`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：决策 1：Schema 以数据库表为准

**决策：** `CONFIG.table` 绑定已注册表；`load_schema()` 为唯一字段契约。

---

## DEC-02：决策 2：单一入口 `DataSourceManager.execute` / `renew`

**决策：** discover → 建 handler → scheduler 拓扑执行。

---

## DEC-03：决策 3：数据源之间串行 + 拓扑序

**决策：** `DataSourceExecutionScheduler` 拓扑排序；reserved dependency 由 `reserved_dependencies` 解析。

---

## DEC-04：决策 4：Provider 全量发现、Handler 按名取用

**决策：** 初始化发现全部 Provider；handler 按 `provider_name` 取用。

---

## DEC-05：决策 5：TQDM 在 import 时禁用

**决策：** `base_handler` 加载时设 `TQDM_DISABLE=1`。

---

## DEC-06：决策 6：日期范围无独立 RenewManager

**决策：** 由 `DateRangeService` / `date_range_helper` / `RenewCommonHelper` 统一计算；已删除未接入的 RenewManager 与三模式 RenewService 占位实现。

---

## DEC-07：决策 7：样本股票宇宙不在本模块

**决策：** 系统内保留哪些股票由 `DataManager.sample_universe` 决定。本模块只在抓取切片与写库过滤时消费，不持有名单文件或 Facade API。

---


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
