#!/usr/bin/env python3
"""entity_based 枚举端到端 smoke：1 股 + 短区间 → JobExecutor → CSV。"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from core.modules.strategy.core.engines.enumerator.pipeline import EnumeratorPipeline
from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
    StrategyDraft,
    StrategyInfo,
)

_DEVTOOLS_STOCK_BASED = (
    PROJECT_ROOT / "devtools" / "performance" / "strategy" / "test_base_strategies" / "stock_based"
)


def _load_strategy() -> EnabledStrategyInfo:
    draft = StrategyDraft(
        unique_relative_path="stock_based",
        strategy_file=_DEVTOOLS_STOCK_BASED / "strategy.py",
        settings_file=_DEVTOOLS_STOCK_BASED / "settings.py",
    )
    info = StrategyInfo.from_draft(draft)
    if info is None:
        raise RuntimeError(f"invalid strategy: {draft.validation_errors()}")
    fields = {key: value for key, value in info.__dict__.items() if not key.startswith("_")}
    return EnabledStrategyInfo(**fields)


def main() -> int:
    strategy = _load_strategy()
    runtime = {
        "sampling": {
            "use_sampling": True,
            "stock_pool": ["600000.SH"],
            "sampling_amount": 1,
            "start_date": "20240101",
            "end_date": "20240331",
        },
    }

    print("=== entity_based enum smoke ===", flush=True)
    started = time.time()
    from core.modules.strategy.contracts import SimulateKind
    from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
        GlobalEntityCache,
    )
    from core.modules.strategy.core.services.simulation_cache.fingerprints import (
        FingerprintCalculator,
    )
    from core.modules.strategy.strategy import SimulateRuntimeContext

    fp_res = FingerprintCalculator.calculate_fingerprints(
        strategy,
        runtime,
        GlobalEntityCache.get_stock_list(),
        GlobalEntityCache.get_latest_completed_trading_date(),
    )
    ctx = SimulateRuntimeContext(
        strategy_info=strategy,
        fp_res=fp_res,
        kind=SimulateKind.ENUMERATE,
        steps=[SimulateKind.ENUMERATE],
    )
    result = EnumeratorPipeline.run(ctx)
    elapsed = time.time() - started

    print("RESULT:", result, flush=True)
    print("elapsed_sec:", round(elapsed, 2), flush=True)

    if not result.get("success"):
        return 1

    output_dir = result.get("output_dir")
    if not output_dir:
        print("missing output_dir", flush=True)
        return 1

    rows = OpportunityCsvHelper.collect_from_dir(Path(output_dir))
    print("csv_rows:", len(rows), flush=True)
    print("opportunities_count:", result.get("opportunities_count"), flush=True)
    if rows:
        print("sample_outcome:", rows[0].get("outcome"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
