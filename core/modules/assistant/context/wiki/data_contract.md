---
title: Data contract 数据契约
aliases:
  - data contract
  - datakey
  - contract issuer
  - data-routing
  - data-injection
  - strategy data settings
summary: NTQ的数据契约的介绍。
---

# 数据合约：DataKey 与 ContractIssuer

## 核心概念

数据合约是 NTQ 数据层的中间层——它位于 `data_manager`（底层领域服务）和策略钩子（消费端）之间，负责定义"有哪些数据可用"、"数据长什么样"、"如何按需加载"。

| 概念                   | 职责                                              |
| -------------------- | ----------------------------------------------- |
| **DataKey**          | 数据合约的字符串标识符，如 `stock.kline.daily`               |
| **Declaration**      | 合约声明，包含 meta（类型/范围/唯一键）和 loader 类               |
| **ContractIssuer**   | 合约发行者，负责发现、注册、签发合约实例                            |
| **BaseDataContract** | 合约实例，持有 meta / runtime / specific / loaded data |

## DataKey

DataKey 是合约的唯一标识。系统内置 DataKey 定义在 `SYS_DATA_KEY` 类中：

```python
from core.modules.data_contract.core.data_contracts.data_keys import SYS_DATA_KEY

SYS_DATA_KEY.STOCK_LIST          # "stock.list"
SYS_DATA_KEY.STOCK_KLINE_DAILY   # "stock.kline.daily"
SYS_DATA_KEY.TRADE_CALENDAR      # "trade.calendar"
```

公共门面 `DATA_KEY` 可直接引用：

```python
from core.modules.data_contract.contracts import DATA_KEY
```

### 内置 DataKey 一览

| Key                                | Scope       | 用途         |
| ---------------------------------- | ----------- | ---------- |
| `stock.list`                       | global      | 股票列表       |
| `stock.kline.daily/weekly/monthly` | per\_entity | K 线数据      |
| `stock.finance.quarterly`          | per\_entity | 季度财务       |
| `stock.indicators.daily`           | per\_entity | 日频技术指标     |
| `stock.adj_factor.eventlog`        | per\_entity | 复权因子事件链    |
| `stock.moneyflow.daily`            | per\_entity | 资金流        |
| `stock.st_periods`                 | per\_entity | ST/\*ST 时段 |
| `index.list`                       | global      | 指数列表       |
| `index.kline.daily`                | per\_entity | 指数日 K      |
| `index.weight.daily`               | per\_entity | 指数权重       |
| `trade.calendar`                   | global      | 交易日历       |
| `macro.gdp/cpi/ppi/pmi/lpr/shibor` | global      | 宏观数据       |
| `tag`                              | global      | 标签数据       |

用户可在 `userspace/extensions/data_contract/` 下定义 `USER_DATA_KEY`，系统会自动合并。

## 合约三层结构

每个合约实例（`BaseDataContract`）包含三层：

| 层            | 类                  | 内容                                                                                                 |
| ------------ | ------------------ | -------------------------------------------------------------------------------------------------- |
| **meta**     | `ContractMeta`     | 静态元数据：key、type（time\_series / non\_time\_series）、scope（global / per\_entity）、unique\_keys、loader 类 |
| **runtime**  | `ContractRuntime`  | 运行时参数：start\_time、end\_time、entity\_ids、base\_time\_field                                          |
| **specific** | `ContractSpecific` | 类型特有字段，如时间轴字段名                                                                                     |

### ContractMeta 关键字段

```python
@dataclass
class ContractMeta:
    key: str                    # DataKey
    type: str                   # "time_series" 或 "non_time_series"
    scope: str                  # "global" 或 "per_entity"
    display_name: str = ""
    description: str = ""
    unique_keys: List[str] = []
    loader: Optional[Type[BaseDataContractLoader]] = None
    list_data_key: str = ""     # per_entity 合约必填，指向实体集合约
```

`list_data_key` 是 per\_entity 合约的必填字段——它指向一个 global 合约（通常是 `stock.list`），用于确定该合约适用于哪些实体。

## 合约声明与发现

### 声明文件

每个合约在 `core/modules/data_contract/core/data_contracts/<key>/` 下有两个文件：

- `declaration.py` — 导出以 `_DECLARATION` 结尾的字典

- `loader.py` — 继承 `BaseDataContractLoader` 的加载器

```python
# declaration.py 示例
STOCK_KLINE_DAILY_DECLARATION = {
    "meta": {
        "key": SYS_DATA_KEY.STOCK_KLINE_DAILY,
        "type": "time_series",
        "scope": "per_entity",
        "display_name": "日K线",
        "unique_keys": ["date"],
        "loader": StockKlineLoader,
        "list_data_key": "stock.list",
    }
}
```

### ContractIssuer 发现流程

`ContractIssuer.discover()` 执行三步：

1. 加载系统 `SYS_DATA_KEY`
2. 扫描 `core/modules/data_contract/core/data_contracts/` 下的声明
3. 扫描 `userspace/extensions/data_contract/` 下的用户声明

验证规则：

- `declaration.py` 和 `loader.py` 必须同时存在

- loader 类必须继承 `BaseDataContractLoader`

- meta 的 `key`、`type`、`scope` 必须有值

- per\_entity 合约必须有 `list_data_key`

- DataKey 必须在合并后的注册表中

- 不允许重复 key

## 合约签发

`ContractIssuer.issue()` 是面向用户的签发方法：

```python
from core.modules.data_contract.contracts import DATA_KEY, ContractIssuer

contract = ContractIssuer.issue(
    DATA_KEY.STOCK_KLINE_DAILY,
    entity_ids=["600000.SH"],
    runtime={
        "start_time": "20200101",
        "end_time": "20201231",
    },
    fill_in_data=True,  # 签发后立即加载数据
)
kline_data = contract.get_data()
```

`fill_in_data=True` 时，合约内部根据 scope 选择加载方式：

- **global 合约**：`loader.load(params)`

- **单实体 per\_entity**：`loader.load(params)`

- **多实体 per\_entity**：`loader.load_batch(entity_ids, params)`

## 数据路由：从策略设置到合约加载

数据路由描述了策略如何从 settings 中声明数据需求，到最终拿到数据的过程。

### 五步路由流程

```
Strategy Settings (settings.py 中的 data.base / data.required)
    ↓
StrategyDataResolver — 归一化声明、注入系统侧载数据、分组
    ↓
ContractIssuer — 签发合约、判断 global / per_entity
    ↓
GlobalEntityCache — 加载全局数据一次，写入共享内存
    ↓
JobBundleLoader — Worker 进程从共享内存读全局数据，签发 per_entity 合约
    ↓
Loaders → DataManager — 底层调用领域服务取数据
```

### StrategyDataResolver

策略 settings 中的 `data` 部分声明数据需求：

```python
data = {
    "base": {"data_key": "stock.kline.daily"},
    "required": [
        {"data_key": "stock.finance.quarterly"},
        {"data_key": "stock.moneyflow.daily"},
    ],
}
```

`StrategyDataResolver` 负责：

- 归一化为 `{data_key, params, indicators, scope}` 结构

- 按 `ContractIssuer.is_global()` 分组为 `global_declarations` 和 `per_entity_declarations`

- 自动注入系统侧载数据（如当 base 是 `stock.kline.*` 时自动注入 `stock.st_periods`）

### GlobalEntityCache

全局数据只加载一次，通过共享内存传递给 Worker 进程：

```python
cache = GlobalEntityCache()
cache.init_system_globals()    # 加载 stock.list + trade.calendar
cache.load_global_declarations(global_declarations)  # 加载额外全局数据
# 写入共享内存供 Worker 读取
```

### JobBundleLoader

Worker 进程中加载 per\_entity 数据：

- 全窗口模式：一次性加载整个回测窗口的数据

- 分片模式：按日历切片加载，减少内存峰值

加载后可通过 `ContractIndicators.apply()` 对数据附加计算指标。

## Loader → DataManager 链

合约的 loader 是数据访问的桥梁。以 `StockKlineLoader` 为例：

```python
class StockKlineLoader(BaseDataContractLoader):
    def load(self, params):
        data_mgr = DataManager()
        kline_service = data_mgr.stock.kline
        rows = kline_service.load_qfq(
            stock_id=params["entity_id"],
            term=params.get("term", "daily"),
            start_date=params.get("start"),
            end_date=params.get("end"),
        )
        return rows

    def load_batch(self, entity_ids, params):
        data_mgr = DataManager()
        return data_mgr.stock.kline.load_batch(ids, ...)
```

合约层不直接访问数据库——所有数据访问都委托给 `DataManager` 的领域服务。

## 特化合约

某些合约需要特殊方法，可以定义子类：

```python
# stock_st_periods/contract.py
class StockStPeriodsContract(BaseTimeSeriesContract):
    def status_tags_at(self, entity_id, trade_date) -> List[str]: ...
    def level_at(self, entity_id, trade_date) -> Optional[str]: ...
```

特化合约从 `contracts.py` 导出：

```python
from core.modules.data_contract.contracts import StockStPeriodsContract
```

## 与其他模块的关系

| 模块                   | 关系                                                     |
| -------------------- | ------------------------------------------------------ |
| **data\_manager**    | 合约 loader 的底层依赖，提供领域数据服务                               |
| **strategy**         | 通过 StrategyDataResolver 声明数据需求，通过 JobBundleLoader 加载数据 |
| **tag**              | 使用数据合约加载标签数据，也通过 ContractIssuer 签发                     |
| **backtest\_engine** | 通过 Timeline 和 callbacks 与数据加载协作                        |

