# Data Contract API 文档

**模块：** `modules.data_contract` · **版本：** `0.4.3`

**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `ContractIssuer`；`DATA_KEY`、基类与专用子类从 [`contracts.py`](./contracts.py) 导入（**不**再从 `contracts` 取 Issuer）。实现位于 `core/`，禁止 deep-import。

---

## ContractIssuer

**描述：** 契约发现、签发与实例化（Facade）

### issue（推荐）

`ContractIssuer.issue(key, entity_ids=None, runtime=None, fill_in_data=False) -> BaseDataContract`

- **类型：** `classmethod`
- **状态：** `beta`
- **描述：** 自动 discovery（进程内一次）；签发空契约或可选立即 `fill_in_data`
- **参数：**
  - `key`：`DATA_KEY.*` 或等价字符串
  - `entity_ids`：`PER_ENTITY` 必填；`GLOBAL` 可不传
  - `runtime`：其余 runtime/params（如 `start_time` / `end_time`）；会与 `entity_ids` 合并
  - `fill_in_data`：是否立即调 loader 取数（默认 `False`）
- **返回：** `BaseDataContract`（时序则为 `BaseTimeSeriesContract` 子类）
- **举例：**

```python
from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import DATA_KEY

contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
rows = contract.get_data()

kline = ContractIssuer.issue(
    DATA_KEY.STOCK_KLINE_DAILY,
    entity_ids=["600000.SH"],
    runtime={"start_time": "20200101", "end_time": "20201231"},
    fill_in_data=True,
)
# 每行：顶层 OHLC = qfq；row["raw"] / row["hfq"] / row["adj_factor"]
```

### discover / get_contract / list_available_keys / reload / …

实例 API（先 `ContractIssuer()` 再 `discover()`）用于检查声明、注册自定义 declaration 等。

- **状态：** `beta`

常用：`get_contract`、`list_available_keys`、`list_system_keys`、`is_available`、`get_list_data_key`、`register_custom_declaration`、`get_declaration`、`system_registry_source_path`、`list_catalog_entries`、`list_ui_catalog_entries` / `fetch_ui_catalog_page`。

#### list_catalog_entries / list_ui_catalog_entries / fetch_ui_catalog_page

`ContractIssuer.list_catalog_entries() -> list[dict]`（classmethod）  
`ContractIssuer.list_ui_catalog_entries(*, force_reload=False) -> list[dict]`（classmethod）  
`ContractIssuer.fetch_ui_catalog_page(page, limit, *, force_reload=False) -> (items, total)`（classmethod）

- **状态：** `beta`
- **描述：** CLI 目录行 / BFF UI 目录行（含 origin、is_custom）。自动 discover；信道勿摸 `_discovered` / `_declarations_cache`

#### scaffold_user_contract / write_user_contract_files / apply_user_data_key / validate_user_contract / describe_user_contract

`ContractIssuer.scaffold_user_contract(*, key, data_key=None, const_name=None, contract_type="non_time_series", scope="global", list_data_key="", display_name="") -> dict`（staticmethod）  
`ContractIssuer.write_user_contract_files(*, key, declaration_py="", loader_py="", contract_py="") -> dict`（staticmethod）  
`ContractIssuer.apply_user_data_key(*, const_name, data_key) -> dict`（staticmethod）  
`ContractIssuer.validate_user_contract(*, key, reload=True) -> dict`（staticmethod）  
`ContractIssuer.describe_user_contract(*, data_key) -> dict`（staticmethod）

- **状态：** `beta`
- **描述：** Userspace 契约脚手架与校验（实现在 `user_contracts`）。`key` 为目录相对路径；`data_key` 为点分键；`apply_user_data_key` 写 `USER_DATA_KEY`。校验默认可 `reload` 生效。

#### reload

`ContractIssuer.reload(user_space_path=None) -> int`

- **类型：** `classmethod`
- **状态：** `beta`
- **描述：** 强制重新扫描系统 + userspace 契约，清空并重建进程内类级缓存（无需重启 NTQ）。userspace 的 `data_keys.py` / `declaration.py` / `loader.py` 会重新读盘。
- **返回：** 发现到的有效 key 数量
- **举例：**

```python
from core.modules.data_contract import ContractIssuer

n = ContractIssuer.reload()
keys = ContractIssuer.get_all_keys()
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `DATA_KEY` / `SYS_DATA_KEY` | 契约键值常量 |
| `BaseDataContract` | meta / runtime / specific 三层基类 |
| `BaseTimeSeriesContract` | 时序扩展（`until` / `normalize_as_of` / `CursorState`） |
| `BaseNonTimeSeriesContract` | 非时序基类 |
| `BaseDataContractLoader` | loader 基类（`load` / `load_batch`） |
| `ContractType` / `ContractScope` | 枚举 |
| `StockStPeriodsContract` | ST 区间专用子类（`issue(DATA_KEY.STOCK_ST_PERIODS)` 返回） |

key 包：`declaration.py` + `loader.py` 必需；可选 `contract.py` + `meta.contract_class`。userspace 同布局并注册 `USER_DATA_KEY`。
