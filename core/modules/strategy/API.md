# Strategy API 文档

**版本：** `0.7.0`  
**最低支持核心版本：** `>=0.4.4`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Strategy`；hooks / 枚举 / 共享数据类从 [`contracts.py`](./contracts.py) 导入。

---

## Strategy

**描述：** 策略 Facade — scan / simulate（enumerate · price_factor · portfolio）/ analyze / discovery

### scan

`Strategy.scan(key_or_id: str | None = None, *, demo: bool = False) -> dict`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** 机会扫描；委托 `ScannerPipeline.scan`
- **参数：**
  - `key_or_id`：策略 key / 相对路径；`None` 时行为由扫描管线决定
  - `demo`：演示模式

### simulate

`Strategy.simulate(key_or_id: str, *, kind: SimulateKind | str = SimulateKind.ENUMERATE, ignore_cache: bool = False, runtime_settings: dict | None = None) -> dict`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** 统一模拟入口（指纹 → 缓存 → Pipeline）；`kind=full` 暂不支持（`ValueError`）
- **参数：**
  - `key_or_id`：策略标识（须已启用）
  - `kind`：`enumerate` / `price_factor` / `portfolio`（或对应 `SimulateKind`）
  - `ignore_cache`：跳过缓存命中
  - `runtime_settings`：运行时覆盖 settings（参与指纹）

### enumerate / price_factor / portfolio

`Strategy.enumerate(key_or_id, ignore_cache=False, runtime_settings=None) -> dict`  
`Strategy.price_factor(key_or_id, ignore_cache=False, runtime_settings=None) -> dict`  
`Strategy.portfolio(key_or_id, ignore_cache=False, runtime_settings=None) -> dict`

- **状态：** `beta`
- **描述：** `simulate` 的薄封装（分别对应 `SimulateKind.ENUMERATE` / `PRICE_FACTOR` / `PORTFOLIO`）

### analyze

`Strategy.analyze(*, session_id: str | None = None) -> None`

- **状态：** `beta`
- **描述：** 读取各启用策略下 price / portfolio 最新 version 摘要并 present；`session_id` 预留未用

### list_strategies / list_enabled_strategies / list_enabled_keys / list_strategy_infos

`Strategy.list_strategies(*, strategies_root: str | None = None) -> list[str]`  
`Strategy.list_enabled_strategies(*, strategies_root: str | None = None) -> list[str]`  
`Strategy.list_enabled_keys() -> list[str]`  
`Strategy.list_strategy_infos(*, enabled_only: bool = False) -> list[dict]`

- **状态：** `beta`
- **描述：** 已发现 / 已启用策略 id（`unique_relative_path`）列表；`list_enabled_keys` 为启用策略的 `meta.key`；`list_strategy_infos` 一次返回元数据字典（含 `folder` / `key` / `is_enabled` 等）。`strategies_root` 预留，当前用 ProjectContext 策略根

### find / get_strategy_info

`Strategy.find(key_or_id: str, *, enabled_only: bool = False) -> dict | None`  
`Strategy.get_strategy_info(strategy_name: str, *, strategies_root: str | None = None) -> dict | None`

- **状态：** `beta`
- **描述：** 按 `meta.key` 或相对路径查找元数据；不存在返回 `None`。`get_strategy_info` 等价于 `find(..., enabled_only=False)`（含 `relative_path` / `unique_relative_path` / `key` / `is_enabled` / `display_name` / `folder` / `settings`）

### resolve / resolve_folder / is_valid_path

`Strategy.resolve(key_or_id: str) -> str`  
`Strategy.resolve_folder(key_or_id: str) -> Path`  
`Strategy.is_valid_path(relative_path: str) -> bool`

- **状态：** `beta`
- **描述：** key/path → 相对 path（缺失 `FileNotFoundError`）；→ 绝对目录（未入库回落 coerce）；脚手架路径段机器可读校验

### clear_workbench_cache

`Strategy.clear_workbench_cache() -> int`

- **状态：** `beta`
- **描述：** 清空 `sys_strategy_workbench_snapshot`；失败 `RuntimeError`；成功返回删除行数

### export_package / import_package

`Strategy.export_package(target: str, *, output_path: str | None = None) -> int`  
`Strategy.import_package(package_path: str, *, force: bool = False, skip_existing: bool = False, dry_run: bool = False) -> int`

- **状态：** `beta`
- **描述：** 策略交流包导出 / bundle 导入（退出码）；供 CLI / system shell 使用，勿 deep-import `PackageCli`

**举例：**

```python
from core.modules.strategy import Strategy
from core.modules.strategy.contracts import SimulateKind

names = Strategy.list_strategies()
info = Strategy.find("demo_strategy", enabled_only=True)
Strategy.scan("demo_strategy")
Strategy.simulate("demo/random/random_v1_null_baseline", kind=SimulateKind.ENUMERATE)
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `StrategyHooks` / `StrategyContext` / `StrategyData` / `StrategyInfo` | userspace hook 契约 |
| `Opportunity` / `Investment` / `CalendarAsOfResult` | 引擎共享数据类 |
| `AsOfSlice` / `JobBundleLoader` / `ProgressRecorder` | 跨模块协作面（tag / BE 数据装载与进度落盘） |
| `ExecutionMode` / `SellReason` / `SimulateKind` / `WorkbenchStep` | 公开枚举 |

### latest_completed_trading_date

`Strategy.latest_completed_trading_date() -> str`

- **状态：** `beta`
- **描述：** 系统最新已收盘交易日（calculation 默认 end 等）
