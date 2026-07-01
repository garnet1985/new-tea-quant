# Data Contract 模块（`modules.data_contract`）

用 **`DataKey`** 声明数据依赖，**`DataContracts.issue`** 签发句柄；加载后 **`DataContracts.until(contract, as_of)`** 做 PIT 前缀裁剪（委托 **`modules.data_cursor`**）。

> 版本 **0.5.0**：Facade 黑盒 cache、`issue`/`load` 拆分、公开 API 契约见 [`api.yaml`](api.yaml)。

## 快速开始

```python
from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import DataKey

dcm = DataContracts()
DataContracts.shared_cache().enter_strategy_run()

issued = dcm.issue(
    DataKey.STOCK_KLINE_DAILY,
    entity_id="000001.SZ",
    start="20240101",
    end="20241231",
    adjust="qfq",
)
contract = issued.require_one()
pit = dcm.until(contract, "20240601")

DataContracts.shared_cache().exit_strategy_run()
```

跨模块类型从 **`contracts.py`** 导入（仅类/枚举）；K 线 slot 等 helper 在 **`core/registry/kline_keys.py`**（模块内部，非公开契约）。

## 目录结构

```text
core/modules/data_contract/
├── data_contract.py       # Facade: DataContracts
├── contracts.py           # 公开类型（类 / 枚举）
├── api.yaml / glossary.yaml
├── core/registry|issue|contract|load|cache/
└── docs/
```

裁剪能力：`DataContracts.until` → [`modules.data_cursor`](../data_cursor/README.md)

## 测试

```bash
python3 -m pytest core/modules/data_contract/__test__/ -q
```

用例注册表与说明见 [`__test__/README.md`](__test__/README.md)、[`__test__/test_cases.yaml`](__test__/test_cases.yaml)。
