# Strategy API 文档

**版本：** `0.8.0`  
**最低支持核心版本：** `>=0.4.4`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。Version / 指纹见 [docs/VERSIONING.md](./docs/VERSIONING.md)。

**公开约定：** 包根仅导出 `Strategy`；hooks / 枚举 / 共享数据类从 [`contracts.py`](./contracts.py) 导入。

---

## Strategy

**描述：** 策略 Facade — scan / simulate（enumerate · price_factor · portfolio）/ discovery

### scan

`Strategy.scan(key_or_id: str | None = None, *, demo: bool = False) -> dict`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** 机会扫描；委托 `ScannerPipeline.scan`
- **参数：**
  - `key_or_id`：策略 key / 相对路径；`None` 时行为由扫描管线决定
  - `demo`：演示模式

### scan_page_context / scan_readiness / scan_block_reason / scan_run

`Strategy.scan_page_context() -> dict`  
`Strategy.scan_readiness(key_or_id: str, *, demo: bool = False) -> dict`  
`Strategy.scan_block_reason(*, demo: bool = False) -> str`  
`Strategy.scan_run(key_or_id: str, *, progress_id: str, demo: bool = False, force: bool = False) -> None`

- **状态：** `beta`
- **描述：** 工作台扫描。读模型在 `ScannerPipeline`（page_context / readiness / block_reason）；`scan_run` 写 `ScanProgress` 后调用 `ScannerPipeline.run`。CLI 用 `scan`（可多策略、无进度文件）。BFF 只负责线程与单飞锁。落盘 `{strategy}/results/scan/{YYYYMMDD}/`（`scan_summary.json` + 有机会时 `opportunities.csv`），读写走 `ArtifactStore.scan_at`。

### simulate

`Strategy.simulate(key_or_id: str, *, kind: SimulateKind | str = SimulateKind.ENUMERATE, ignore_cache: bool = False, runtime_settings: dict | None = None) -> dict`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** 统一模拟入口（指纹 → 磁盘 `simulations/meta.json` registry → Pipeline）；`kind=full` 暂不支持（`ValueError`）。规则见 [docs/VERSIONING.md](./docs/VERSIONING.md)。
- **参数：**
  - `key_or_id`：策略标识（须已启用）
  - `kind`：`enumerate` / `price_factor` / `portfolio`（或对应 `SimulateKind`）
  - `ignore_cache`：跳过磁盘 cache 命中（仍按双指纹写入已有 vid，不新开号）
  - `runtime_settings`：运行时覆盖 settings（参与指纹）
- **返回：** 目标 step 槽位 dict（如 `enumerate` / `price_factor` / `portfolio`）+ 顶层 `version_id`（字符串）。cache hit 时直接返回已存在 step 产物摘要（`success` / `output_dir` / `version_id`）；UI 指标由 BFF `report_hydrate` 从 `overall_report.json` 补全。
- **环境失效：** registry 中 `env_fp` 与当前运行环境不一致时不可 cache hit（配置相同也会 miss 并新建 version）；BFF 读 version 时返回 `env_invalid: true`。
- **强制重跑：** `ignore_cache=True`（CLI `--force`）跳过 cache 命中，price/portfolio **不复用**已有 enum 产物（会重跑 enum）。命中键 `(execute_fp, env_fp)` 不变则 **写入同一 `version_id`**，复写上游步时清下游。禁止为同一双指纹再 allocate 一个号。
- **磁盘布局：** `{strategy}/results/simulations/{version_id}/{enum|price|portfolio}/`；索引在 `simulations/meta.json`（`registry` + `next_version_id` + 根上 `pinned`）；`{version_id}/` 归档 `settings.json` / `effective_settings.json` / `scope.json`。

### enumerate / price_factor / portfolio

`Strategy.enumerate(key_or_id, ignore_cache=False, runtime_settings=None) -> dict`  
`Strategy.price_factor(key_or_id, ignore_cache=False, runtime_settings=None) -> dict`  
`Strategy.portfolio(key_or_id, ignore_cache=False, runtime_settings=None) -> dict`

- **状态：** `beta`
- **描述：** `simulate` 的薄封装（分别对应 `SimulateKind.ENUMERATE` / `PRICE_FACTOR` / `PORTFOLIO`）

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

### resolve / resolve_path / resolve_folder / is_valid_path

`Strategy.resolve(key_or_id: str) -> str`  
`Strategy.resolve_path(key_or_id: str) -> str`  
`Strategy.resolve_folder(key_or_id: str) -> Path`  
`Strategy.is_valid_path(relative_path: str) -> bool`

- **状态：** `beta`
- **描述：** key/path → 稳定身份 `meta.key`（缺 key 时回落 path；DB / 进度 / UI 用）；→ userspace 相对 path（打包与路径型 API）；→ 绝对目录（未入库回落 coerce）；脚手架路径段机器可读校验

### load_price_entity_investments / price_overall_report_path

`Strategy.load_price_entity_investments(version_dir: Path, entity_id: str) -> list`  
`Strategy.price_overall_report_path(version_dir: Path) -> Path`

- **状态：** `beta`
- **描述：** 读取 price_factor 产物（实体 investments / overall_report 路径）。Scan 分发时由内部 enrichment 组装 `context["price_history"]` 推给 adapter；跨模块勿 deep-import `report_manager`

### present_report

`Strategy.present_report(kind: SimulateKind | str, output_dir: str | Path, *, stream=None) -> None`

- **状态：** `beta`
- **描述：** 从 `output_dir` 展示 enumerate / price_factor / portfolio 终局摘要（CLI 模拟结束后）；勿 deep-import 各引擎 `ReportManager`

### present_analysis_report

`Strategy.present_analysis_report(output_dir: str | Path, *, stream=None) -> None`

- **状态：** `beta`
- **描述：** 从仿真 `output_dir` 读取 `analysis/report.json` 并打印归因终端摘要（`sa` 生成后调用）；内部为 `AnalysisReportPresenter.load(...).present(...)`；缺失文件则 `FileNotFoundError`

### step_analysis_from_output_dir / resolve_step_analysis / resolve_simulation_output_dirs

`Strategy.step_analysis_from_output_dir(output_dir: str | Path) -> dict`  
`Strategy.resolve_step_analysis(strategy_name: str, step: str, slot: dict | None = None, *, workbench_version: int = 0) -> dict`  
`Strategy.resolve_simulation_output_dirs(strategy_name: str, *, step: str, slot: dict | None = None, workbench_version: int = 0) -> list[Path]`

- **状态：** `beta`
- **描述：** 归因读取与 step 产物目录解析（BFF step report / hydrate 用）。`step_analysis_from_output_dir` 读单目录 `analysis/report.json` → `{available, report_path, facts, insights}`（`facts` 给 UI 数字，`insights` 给 CLI 叙事）；`resolve_step_analysis` 按 slot + workbench version 候选目录解析；`resolve_simulation_output_dirs` 返回 enum / price / portfolio 的绝对 version-dir 候选列表。BFF `GET …/report/:step/:version` 的 `analysis` 含 `enabled`、`facts`（含科学 `buckets` 与合成 `tiers`）和 `conclusion`（headline / key_findings / explains，来自 insights 切片），不下发完整 `insights`
- **生成：** simulate 且 `settings.analysis.enabled=true` 时在主 simulate 步结束后自动生成 report；无独立 `Strategy.analyze`

### prune_simulation_results / prune_scan_results

`Strategy.prune_simulation_results(key_or_id: str, *, kind: str | None = None, max_versions: int | None = None) -> dict`  
`Strategy.prune_scan_results(key_or_id: str, *, max_versions: int | None = None) -> dict`  
`Strategy.delete_simulation_version(key_or_id: str, version: int | str) -> dict`  
`Strategy.set_simulation_version_pinned(key_or_id: str, version: int | str, pinned: bool) -> dict`

- **状态：** `beta`
- **描述：** 磁盘 simulation keep-N（按 **version 目录** 粒度）。默认上限来自 `data.json` → `retention`（`simulation_results_max_versions` / `scan_results_max_versions`，可被 `userspace/config/data.json` 同名覆盖）。`kind` 为 `enum` / `price` / `portfolio`；`None` 表示整个 version 目录 prune。删单 version 用 `delete_simulation_version`（CLI `sdv`、BFF `DELETE …/version/:id/cache`，内部 `ArtifactRetention.clear_by_version`）；批量清磁盘用 `TempCleanup.clear_backtest_results_disk` 或 `ArtifactRetention.clear_all`。触顶时 **allocate 拒绝**，不静默删。`delete_simulation_version` 的 `version` 接受 `3` / `v3`，只删产物目录与 registry，不改 `settings.py`；已固定的也可删，并同步从 meta.`pinned` 拿掉。`set_simulation_version_pinned` 只改 `simulations/meta.json` 根上的 `pinned` 列表（CLI `spn` / `sup`，BFF `POST|DELETE …/version/:id/pin`）。自动清理与「即将清理」标记都先读 `pinned`。

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
| `StrategyHooks` / `StrategyContext` / `StrategyData` / `StrategyInfo` | userspace hook 契约；`has_opportunity() -> bool`；`ctx.remember/recall/forget` 为内存袋，`ctx.capture` 为本笔归因输入 |
| `Opportunity` / `Investment` / `CalendarAsOfResult` | 引擎共享数据类；`Opportunity.signal_snapshot` 为归因用决策现场记录 |
| `AsOfSlice` / `JobBundleLoader` / `ProgressRecorder` | 跨模块协作面（tag / BE 数据装载与进度落盘） |
| `ExecutionMode` / `SellReason` / `SimulateKind` / `WorkbenchStep` | 公开枚举 |

### latest_completed_trading_date

`Strategy.latest_completed_trading_date() -> str`

- **状态：** `beta`
- **描述：** 系统最新已收盘交易日（calculation 默认 end 等）
