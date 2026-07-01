# Strategy Context 三层递进

```
DiscoveredStrategy          Layer 1  discovery
    ↓ StrategyContext.from_discovered()
StrategyContext             Layer 2  engine 入口（diff + 指纹环境）
    ↓ BacktestRuntimeContext.from_strategy_context()
BacktestRuntimeContext      Layer 3  回测 runtime（jobs / performance）
    ↓ EntityBasedRuntimeContext / SliceBasedRuntimeContext
RuntimeStatus               可变状态（与 context 分离，挂在 BacktestRuntime）
```

## Layer 1 — `DiscoveredStrategy`

Discovery 产物，满足即可 **runnable**：

- **id**：`key`（meta.key，全局唯一）、`id`（strategies 下相对路径）
- **位置**：`strategies_root`, `folder`, `strategy_file`, `settings_file`
- **模块**：`worker_class`, `worker_module_path`, `worker_class_name`, `worker_file_path`

校验：`settings.py` + `strategy.py` + `meta.key` + hooks 继承 `StrategyHooks`

## Layer 2 — `StrategyContext`

Engine 入口，在 Layer 1 上追加：

- `effective_settings`, `settings_diff`
- 指纹环境：`entity_ids`, `start_date`, `end_date`, `fingerprint_hash`
- 输出：`userspace_root`, `output_dir`, `version_id`, …

工厂：`StrategyContext.from_discovered(discovered, userspace_root=..., user_settings=...)`

## Layer 3 — `BacktestRuntimeContext`

回测执行期，在 Layer 2 上追加：

- `execution_mode`, `jobs`, `performance`, `global_data_meta`, `task_name`, …

模式特化：`EntityBasedRuntimeContext` / `SliceBasedRuntimeContext`

## 数据流

```
Strategy.enumerate(name)
  → DiscoveryService.load_strategy() → DiscoveredStrategy
  → EnumeratorEngine(discovered).run()
      → StrategyContext.from_discovered(...)
      → pipeline.build_runtime → EntityBasedRuntimeContext.from_strategy_context(...)
      → BacktestRuntime(context, status)
```
