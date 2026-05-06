"""V2-05：触发单步回测（后台线程执行引擎 flow）。

模块顶层避免导入 ``price_factor`` / ``capital_allocation`` / ``enumerator``，以免经 DbCache
链式导入 ``cache_service`` → BFF（Flask）。
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional, Tuple

from core.infra.project_context.path_manager import PathManager
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import DiscoveredStrategy
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper
from core.modules.strategy.services.launcher.strategy_settings_service import StrategySettingsService
from core.modules.strategy.services.launcher.workbench_jobs import job_create, job_update

logger = logging.getLogger(__name__)

_VALID_STEPS = frozenset({"enum", "price", "capital"})


def normalize_step(step: str) -> Optional[str]:
    s = str(step or "").strip().lower()
    return s if s in _VALID_STEPS else None


def _resolve_discovered(
    strategy_name: str, api_settings: Dict[str, Any]
) -> Tuple[Optional[DiscoveredStrategy], Optional[str]]:
    folder = PathManager.userspace() / "strategies" / strategy_name
    base = StrategyDiscoveryHelper.load_strategy(folder)
    if base is None:
        return None, "策略不存在或无法加载"

    normalized, err = StrategySettingsService.normalize_runtime_settings(
        strategy_name=strategy_name,
        api_settings=api_settings,
    )
    if err or not normalized:
        return None, err or "settings 校验失败"

    st = StrategySettings(raw_settings=dict(normalized))
    vr = st.validate()
    if not vr.is_usable():
        return None, "settings 校验失败"

    discovered = DiscoveredStrategy(
        name=base.name,
        folder=base.folder,
        worker_class=base.worker_class,
        worker_module_path=base.worker_module_path,
        worker_class_name=base.worker_class_name,
        settings=st,
    )
    discovered.validate_required_fields()
    return discovered, None


def _run_step_and_snapshot_id(
    step: str,
    strategy_name: str,
    discovered: DiscoveredStrategy,
    *,
    is_force: bool,
    job_id: str,
) -> int:
    """惰性导入引擎（避免测试环境无 Flask 时导入失败）。"""
    if step == "enum":
        from core.modules.strategy.services.launcher.enumerator_runtime_service import (
            EnumeratorRuntimeService,
        )

        ctx = EnumeratorRuntimeService.build_context(
            strategy_name=strategy_name,
            strategy_info=discovered,
            raw_settings_override=discovered.settings.to_dict(),
            force_refresh=is_force,
            workbench_run_id=job_id,
            workbench_strategy_name=strategy_name,
        )
        EnumeratorRuntimeService.run_enum(ctx)
        return int(ctx.flow.last_snapshot_id or 0)

    if step == "price":
        from core.modules.strategy.engines.simulator.price_factor.price_factor_flow import PriceFactorFlow

        flow = PriceFactorFlow(is_verbose=False, force_refresh=is_force)
        flow.run(strategy_name, discovered)
        return int(flow.last_snapshot_id or 0)

    if step == "capital":
        from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow import (
            CapitalAllocationFlow,
        )

        flow = CapitalAllocationFlow(is_verbose=False, force_refresh=is_force)
        flow.run(strategy_name, discovered)
        return int(flow.last_snapshot_id or 0)

    raise ValueError(f"未知 step: {step!r}")


def _background_job(
    job_id: str,
    strategy_name: str,
    step: str,
    discovered: DiscoveredStrategy,
    is_force: bool,
) -> None:
    job_update(job_id, status="running", progress=1.0)
    try:
        job_update(job_id, progress=5.0)
        sid = _run_step_and_snapshot_id(
            step,
            strategy_name,
            discovered,
            is_force=is_force,
            job_id=job_id,
        )
        job_update(
            job_id,
            status="completed",
            progress=100.0,
            snapshot_id=int(sid or 0),
        )
    except Exception as exc:  # noqa: BLE001 — 任务边界兜底
        logger.exception("Workbench step run failed job_id=%s", job_id)
        job_update(job_id, status="failed", progress=100.0, error=str(exc))


def trigger_workbench_step_run(
    *,
    strategy_name: str,
    step: str,
    api_settings: Dict[str, Any],
    is_force: bool,
) -> Dict[str, Any]:
    """
    校验并入队后台任务。

    返回 ``{"is_triggered": True, "job_id": "..."}`` 或
    ``{"is_triggered": False, "reason": "..."}``。
    """
    norm_step = normalize_step(step)
    if norm_step is None:
        return {"is_triggered": False, "reason": f"step 须为 enum / price / capital，收到 {step!r}"}

    name = str(strategy_name or "").strip()
    if not name:
        return {"is_triggered": False, "reason": "strategy_name 无效"}

    discovered, err = _resolve_discovered(name, api_settings)
    if err or discovered is None:
        return {"is_triggered": False, "reason": err or "无法解析策略"}

    jid = job_create(strategy_name=name, step=norm_step, is_force=is_force)
    thread = threading.Thread(
        target=_background_job,
        args=(jid, name, norm_step, discovered, is_force),
        daemon=True,
        name=f"workbench-run-{jid[:8]}",
    )
    thread.start()
    return {"is_triggered": True, "job_id": jid}
