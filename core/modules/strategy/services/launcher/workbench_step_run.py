"""工作台单步运行：进程内 job 表（V2-06）、触发 run（V2-05）。

模块顶层避免导入 ``price_factor`` / ``capital_allocation`` / ``enumerator``，以免经 DbCache
链式导入 ``cache_service`` → BFF（Flask）。
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional, Tuple

from core.infra.project_context.path_manager import PathManager
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import DiscoveredStrategy
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper
from core.modules.strategy.services.launcher.run_service import StrategySettingsService

logger = logging.getLogger(__name__)

_VALID_STEPS = frozenset({"enum", "price", "capital"})

# --- 进程内 job 表 ---

_LOCK = threading.Lock()
_JOBS: Dict[str, Dict[str, Any]] = {}


def job_create(*, strategy_name: str, step: str, is_force: bool) -> str:
    jid = str(uuid.uuid4())
    name = str(strategy_name).strip()
    st = str(step).strip()
    with _LOCK:
        _JOBS[jid] = {
            "strategy_name": name,
            "step": st,
            "is_force": bool(is_force),
            "progress": 0.0,
            "status": "queued",
            "error": None,
            "snapshot_id": 0,
        }
    return jid


def job_resolve_id(
    strategy_name: str,
    normalized_step: str,
    job_id: str,
) -> Optional[str]:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    name = str(strategy_name).strip()
    step_key = str(normalized_step).strip()
    row = job_get(jid)
    if not row:
        return None
    if row.get("strategy_name") != name or row.get("step") != step_key:
        return None
    return jid


def job_update(job_id: str, **fields: Any) -> None:
    with _LOCK:
        row = _JOBS.get(job_id)
        if row is None:
            return
        row.update(fields)


def job_get(job_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        row = _JOBS.get(job_id)
        return dict(row) if row else None


def _fed_result_report_slice(
    strategy_name: str,
    normalized_step: str,
    snapshot_id: int,
) -> Dict[str, Any]:
    """从工作台快照 ``result_report`` 取出当前 step  execution 条需要的摘要（与 FED 执行面板字段对齐）。"""
    if snapshot_id <= 0:
        return {}
    try:
        from core.modules.strategy.services.launcher.workbench import (
            fetch_workbench_snapshot_by_snapshot_id,
        )
    except Exception:
        return {}

    row = fetch_workbench_snapshot_by_snapshot_id(
        str(strategy_name).strip(),
        int(snapshot_id),
    )
    if not row:
        return {}
    rr = row.get("result_report") or {}
    out: Dict[str, Any] = {}

    if normalized_step == "enum":
        raw = rr.get("enum")
        if isinstance(raw, dict) and raw:
            merged = dict(raw)
            try:
                merged["opportunities"] = int(merged.get("opportunities", 0) or 0)
            except (TypeError, ValueError):
                merged["opportunities"] = 0
            out["enum"] = merged

    elif normalized_step == "price":
        raw = rr.get("price_factor")
        if isinstance(raw, dict) and raw:

            def _num(val: Any, default: float = 0.0) -> float:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            win = _num(
                raw.get("winRate", raw.get("win_rate", raw.get("win_pct"))),
            )
            roi = _num(raw.get("roi", raw.get("avg_roi", raw.get("roi_pct"))))
            out["price"] = {"winRate": round(win, 2), "roi": round(roi, 2)}

    elif normalized_step == "capital":
        raw = rr.get("capital_allocation")
        if isinstance(raw, dict) and raw:

            def _num(val: Any, default: float = 0.0) -> float:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            profit = _num(raw.get("profit", raw.get("total_profit")))
            ic = _num(raw.get("initialCapital", raw.get("initial_capital")))
            ec = _num(raw.get("endCapital", raw.get("end_capital")))
            if ec == 0.0 and (ic != 0.0 or profit != 0.0):
                ec = ic + profit
            ret_pct = _num(raw.get("retPct", raw.get("return_pct", raw.get("ret_pct"))))
            out["capital"] = {
                "profit": profit,
                "retPct": round(ret_pct, 4),
                "initialCapital": ic,
                "endCapital": ec,
            }

    return out


def _progress_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    progress = round(float(row.get("progress") or 0), 2)
    status = str(row.get("status") or "unknown")
    out: Dict[str, Any] = {"progress": progress, "status": status}
    if status == "completed":
        out["is_success"] = True
        sid = int(row.get("snapshot_id") or 0)
        if sid > 0:
            out["snapshot_id"] = sid
            out["version_id"] = f"v{sid}"
    elif status == "failed":
        out["is_success"] = False
        err = row.get("error")
        if err:
            out["reason"] = str(err)
    else:
        out["is_success"] = None
    return out


def get_step_progress(
    *,
    strategy_name: str,
    normalized_step: str,
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """V2-06：``job_id`` 须与路径一致；否则 ``None``。"""
    jid = job_resolve_id(strategy_name, normalized_step, job_id)
    if not jid:
        return None
    row = job_get(jid)
    if not row:
        return None
    payload = _progress_payload(row)
    payload["job_id"] = jid
    if str(row.get("status") or "") == "completed":
        sid = int(row.get("snapshot_id") or 0)
        fed = _fed_result_report_slice(strategy_name, normalized_step, sid)
        if fed:
            payload["result_report"] = fed
    return payload


# --- V2-05：后台线程执行 flow，HTTP 立即返回 job_id 供轮询 ---
#
# 枚举耗时较长时，若在请求线程内同步执行，浏览器会一直阻塞在 POST 上无法渲染进度。
# 另启线程运行步骤；ProcessWorker 在非主线程初始化时需跳过 ``signal.signal``（见
# ``process_worker._setup_signal_handlers``）。


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
