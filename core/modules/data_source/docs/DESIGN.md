# Data Source 设计说明

**版本：** `0.3.6`

本文档描述 **userspace 配置布局**、**schema 来源**与 **handler 发现规则**。实现以 `data_source_manager.py`、`service/manager_helper.py` 为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## userspace 布局

| 路径 | 作用 |
| --- | --- |
| `userspace/data_source/mapping.py` | 定义 **`DATA_SOURCES`**（见 `DataSourceManagerHelper.discover_mappings`） |
| `userspace/data_source/handlers/<name>/config.py` | 各数据源 **`CONFIG`**（顶层 **`table`** 绑定物理表名） |
| `userspace/data_source/handlers/.../handler.py`（或 mapping 指向的模块） | **Handler** 类实现 |
| `userspace/data_source/providers/` | **Provider** 包，供 `ClassDiscovery` 扫描 |

---

## Schema 与表绑定

- **`DataSourceConfig`** 顶层 **`table`** → **`DataManager.get_table(table_name)`** → **`model.load_schema()`** 得到 **dict schema**。
- Handler 输出需与该 schema 对齐；**不写独立 schema 文件**。

---

## Config 发现顺序

1. **`PathManager.data_source_handler(data_source_key)/config.py`**
2. 不存在则在 **`handlers/`** 下递归查找 ``**/{key}/config.py``（`Discovery.file.find_in_tree`）

---

## Provider 发现

- **`DataSourceProviderHelper.discover_provider_classes()`** 使用 **`ClassDiscovery`** 扫描 **`userspace.data_source.providers`**，将 **`BaseProvider`** 子类注册为可实例化 Provider（细节见 `provider_helper.py`）。

---

## 执行与 `is_dry_run`

- CONFIG 顶层 **`is_dry_run`**（经 `DataSourceConfig.get_is_dry_run()`）为真时：**跳过写库**，仍可走抓取与标准化（见 Handler 管线）。

---

## 相关文档

- [API.md](API.md)
- [DECISIONS.md](DECISIONS.md)

---

## 设计决策（原 DECISIONS.md）

# Data Source 设计决策

**版本：** `0.3.6`

---

## 决策 1：Schema 以数据库表为准

**背景（Context）**  
避免维护两套 schema（文件 + 表结构）。

**决策（Decision）**  
每个数据源的 **`CONFIG.table`** 绑定一张已注册表；框架用 **`load_schema()`** 作为唯一字段契约。

**理由（Rationale）**  
与迁移、ORM 一致；减少漂移。

**影响（Consequences）**  
改字段需先改表/模型，再调 handler 映射。

---

## 决策 2：单一入口 `DataSourceManager.execute`

**背景（Context）**  
CLI 或定时任务需要一次跑完全部启用数据源。

**决策（Decision）**  
**`execute()`** 完成 discover → 建 handler → **`scheduler.run`**。

**理由（Rationale）**  
统一缓存清理与执行顺序。

**影响（Consequences）**  
单测单个 handler 需自行实例化或依赖 mapping 启用项。

---

## 决策 3：数据源之间串行 + 拓扑序

**背景（Context）**  
部分 handler 依赖其它数据源产出（如列表、交易日）。

**决策（Decision）**  
**`DataSourceExecutionScheduler`** 对 handler **拓扑排序**，依赖先执行；预留 **reserved dependency**（如 ``latest_completed_trading_date``）由 **`reserved_dependencies`** 解析。

**理由（Rationale）**  
确定性的上下文注入，避免竞态。

**影响（Consequences）**  
长链路尾部失败需看重试与日志。

---

## 决策 4：Provider 全量发现、Handler 按名取用

**背景（Context）**  
同一 Provider 可被多个 handler 共用。

**决策（Decision）**  
初始化时 **发现并实例化当前项目内全部 Provider**；handler 仅按 **provider_name** 从 dict 取用。

**理由（Rationale）**  
简化配置，不必在 mapping 里重复声明「要加载哪些 provider」。

**影响（Consequences）**  
无关 Provider 也会初始化；需注意认证与副作用。

---

## 决策 5：TQDM 在 import 时禁用

**背景（Context）**  
akshare 等库会刷屏进度条。

**决策（Decision）**  
**`base_handler.py` 模块加载时设置 `TQDM_DISABLE=1`**。

**理由（Rationale）**  
与框架日志混排可读性极差。

**影响（Consequences）**  
全局禁用 tqdm 进度条（仅该进程内环境变量语义）。

