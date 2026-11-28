# Data Source — 设计与决策

**模块：** `modules.data_source` · **版本：** `0.4.1`

**最低支持核心版本：** `>=0.5.0`

本文记录本模块的设计目标、方案思路与拍板决策。API 以根目录 [API.md](../API.md) 为准。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

提供配置驱动的数据抓取，支持按照不同模式和不同数据供应商请求并加载数据：新数据源只需在 userspace 加 Provider + Handler，不用改主流程。

## 方案与思路

- **配置驱动**：`DATA_SOURCES` 声明各数据源（`userspace/data_source/mapping.py`）；handler config 经约定路径或 `handlers/` 树内按 key 查找；Provider 扫描 `userspace.data_source.providers` 下 `BaseProvider` 子类（见 DEC-04）。
- **Schema 与表绑定**：不维护独立 schema 文件——`CONFIG.table` → `DataManager.get_table` → `load_schema()`，Handler 输出与 schema 对齐（见 DEC-01）。
- **执行与 `is_dry_run`**：`is_dry_run` 为真时跳过写库，仍可抓取与标准化。
- 其余选型——单一入口 `execute` / `renew`、数据源间串行 + 拓扑序、TQDM 在 import 时禁用、日期范围无独立 RenewManager、样本股票宇宙归属——见下文 DEC-02 ~ DEC-07。

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
- [API.md](../API.md)
- [术语表](../glossary.yaml)
