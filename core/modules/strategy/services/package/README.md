# Strategy Package（策略交流包）

在 `infra.export_import` 之上编排**策略分享包**：导出策略目录及其 settings 解析出的 tag / adapter 依赖。

## API

```python
from core.infra.export_import import ConflictPolicy
from core.modules.strategy.services.package import (
    export_strategy_bundle,
    preview_strategy_bundle_import,
    import_strategy_bundle,
)

manifest, blob = export_strategy_bundle("example")

preview = preview_strategy_bundle_import(blob, policy=ConflictPolicy.SKIP_EXISTING)
result = import_strategy_bundle(blob, ConflictPolicy.SKIP_EXISTING)
```

## 依赖解析

- **strategy**：`userspace/strategies/<name>/`（含 `stock_lists/` 等子路径；排除 `results/`）
- **tag**：`data.extra_required_data_sources` 中 `data_id=tag`，`params.tag_scenario` / `scenario_name`
- **adapter**：`scanner.adapters` 中非内置名（默认跳过 `console`）

## 测试

```bash
python3 -m pytest core/modules/strategy/services/package/__test__/ -q
```
