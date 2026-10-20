"""后台启动回测、归因、滚动对照和扫描。模型只提交策略名，任务立刻返回。"""

from __future__ import annotations

import logging
import threading
import uuid
from pathlib import Path
from typing import Any, Callable, Dict

from core.infra.project_context import ProjectContext
from core.infra.task_guard import TaskGuard
from core.infra.task_guard.contracts import TaskLeaseBusyError
from core.modules.agent.core.code.tools.strategy._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)
from core.modules.agent.core.code.tools.task_record import write_task
from core.modules.agent.core.code.tools.strategy.validate_strategy import validate_strategy
from core.modules.strategy import Strategy
from core.modules.strategy.core.services.progress import (
    ATTRIBUTE_PIPELINE,
    ROLLING_PIPELINE,
    PipelineProgress,
)

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ACTIVE: Dict[str, str] = {}
Runner = Callable[[str, PipelineProgress], Dict[str, Any]]


def start_enumerate(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """启动枚举。区间以 settings 为准。"""
    return _start(
        arguments,
        prefix="enum",
        label="枚举",
        pipeline_name="enum",
        lease_kind="strategy_run",
        runner=_run_enumerate,
    )


def start_price_factor(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """启动价格回测。缺枚举产物时由策略模块自己补跑。"""
    return _start(
        arguments,
        prefix="price",
        label="价格回测",
        pipeline_name="price",
        lease_kind="strategy_run",
        runner=_run_price,
    )


def start_portfolio(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """启动资金模拟。"""
    return _start(
        arguments,
        prefix="port",
        label="资金模拟",
        pipeline_name="portfolio",
        lease_kind="strategy_run",
        runner=_run_portfolio,
    )


def start_simulate(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """依次跑枚举、价格、资金。任一层失败即停。"""
    return _start(
        arguments,
        prefix="sim",
        label="完整回测",
        pipeline_name="enum",
        lease_kind="strategy_run",
        runner=_run_simulate,
    )


def start_attribute_enumerate(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """枚举层归因。须已有主 version。"""
    return _start(
        arguments,
        prefix="atenum",
        label="枚举归因",
        pipeline_name=ATTRIBUTE_PIPELINE,
        lease_kind="strategy_attribute",
        runner=_run_attribute_enumerate,
    )


def start_attribute_price(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """价格层归因。须已有主 version。"""
    return _start(
        arguments,
        prefix="atprice",
        label="价格归因",
        pipeline_name=ATTRIBUTE_PIPELINE,
        lease_kind="strategy_attribute",
        runner=_run_attribute_price,
    )


def start_attribute_portfolio(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """资金层归因。须已有主 version。"""
    return _start(
        arguments,
        prefix="atport",
        label="资金归因",
        pipeline_name=ATTRIBUTE_PIPELINE,
        lease_kind="strategy_attribute",
        runner=_run_attribute_portfolio,
    )


def start_rolling(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """按 rolling.py 做滚动对照。"""
    return _start(
        arguments,
        prefix="roll",
        label="滚动对照",
        pipeline_name=ROLLING_PIPELINE,
        lease_kind="strategy_rolling",
        runner=_run_rolling,
    )


def start_scan(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """扫描当前交易日的机会。不接受 demo 或 force。"""
    from core.modules.strategy.core.services.progress import ScanProgress

    gated = _gate(arguments, "扫描")
    if isinstance(gated, dict):
        return gated
    block = Strategy.scan_block_reason(demo=False)
    if block:
        return {"ok": False, "key": gated, "error": block}

    task_id = f"scan-{uuid.uuid4().hex[:12]}"
    if not _claim(gated, task_id):
        return {"ok": False, "key": gated, "error": "该策略已有任务在运行"}
    try:
        ScanProgress.for_job(gated, task_id).seed(demo=False, force=False)
        write_task({"task_id": task_id, "key": gated, "kind": "scan"})
    except Exception as exc:
        _release(gated, task_id)
        logger.exception("seed scan failed key=%s", gated)
        return {"ok": False, "key": gated, "error": f"无法登记扫描任务: {exc}"}

    thread = threading.Thread(
        target=_scan_worker,
        args=(gated, task_id),
        daemon=True,
        name=f"ntq-scan-{task_id[-6:]}",
    )
    thread.start()
    return {
        "ok": True,
        "key": gated,
        "task_id": task_id,
        "status": "running",
        "note": "扫描已启动。完成前不要编写机会名单",
    }


def _gate(arguments: Dict[str, Any], label: str) -> str | Dict[str, Any]:
    parsed = parse_strategy_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, relative = located
    if not folder.is_dir():
        return {"ok": False, "error": f"策略不存在: {relative}。请先 create_strategy"}

    checked = validate_strategy({"key": parsed})
    if not checked.get("ok"):
        return {
            "ok": False,
            "key": parsed,
            "error": f"策略尚未通过校验，没有启动{label}",
            "errors": checked.get("errors") or [checked.get("error") or "校验失败"],
        }

    info = Strategy.find(parsed)
    if not info or not info.get("is_enabled"):
        return {"ok": False, "key": parsed, "error": f"策略不存在或未启用: {parsed}"}

    status = TaskGuard.read_status()
    if status.get("busy"):
        kind = str(status.get("kind") or "unknown")
        return {
            "ok": False,
            "key": parsed,
            "error": f"系统任务进行中（{kind}），请稍后再试",
        }
    return parsed


def _scan_worker(key: str, task_id: str) -> None:
    from core.modules.strategy.core.services.progress import ScanProgress

    lease = TaskGuard.lease(
        kind="strategy_scan",
        job_id=task_id,
        resource_key=key,
        label=f"strategy_scan:{key}:扫描",
        domains=["data", "strategy"],
    )
    try:
        lease.acquire()
    except TaskLeaseBusyError as exc:
        ScanProgress.for_job(key, task_id).fail(str(exc))
        _release(key, task_id)
        return
    try:
        Strategy.scan_run(key, progress_id=task_id, demo=False, force=False)
    except Exception:
        logger.exception("扫描 failed key=%s task=%s", key, task_id)
    finally:
        try:
            lease.release()
        except Exception:
            logger.exception("lease release failed task=%s", task_id)
        _release(key, task_id)


def _start(
    arguments: Dict[str, Any],
    *,
    prefix: str,
    label: str,
    pipeline_name: str,
    lease_kind: str,
    runner: Runner,
) -> Dict[str, Any]:
    gated = _gate(arguments, label)
    if isinstance(gated, dict):
        return gated
    parsed = gated

    task_id = f"{prefix}-{uuid.uuid4().hex[:12]}"
    if not _claim(parsed, task_id):
        return {"ok": False, "key": parsed, "error": "该策略已有任务在运行"}

    try:
        PipelineProgress.seed(
            parsed,
            task_id,
            pipeline_name=pipeline_name,
            pipeline_description=PipelineProgress.pipeline_description(pipeline_name),
        )
        write_task({"task_id": task_id, "key": parsed, "kind": prefix})
    except Exception as exc:
        _release(parsed, task_id)
        logger.exception("seed %s failed key=%s", prefix, parsed)
        return {"ok": False, "key": parsed, "error": f"无法登记{label}任务: {exc}"}

    thread = threading.Thread(
        target=_worker,
        args=(parsed, task_id, lease_kind, label, runner),
        daemon=True,
        name=f"ntq-{prefix}-{task_id[-6:]}",
    )
    thread.start()
    return {
        "ok": True,
        "key": parsed,
        "task_id": task_id,
        "status": "running",
        "note": f"{label}已启动。不要等待结束，也不要在进度完成前编写结果数字",
    }


def _claim(key: str, task_id: str) -> bool:
    with _LOCK:
        if _ACTIVE.get(key):
            return False
        _ACTIVE[key] = task_id
        return True


def _release(key: str, task_id: str) -> None:
    with _LOCK:
        if _ACTIVE.get(key) == task_id:
            _ACTIVE.pop(key, None)


def _worker(
    key: str,
    task_id: str,
    lease_kind: str,
    label: str,
    runner: Runner,
) -> None:
    lease = TaskGuard.lease(
        kind=lease_kind,
        job_id=task_id,
        resource_key=key,
        label=f"{lease_kind}:{key}:{label}",
        domains=["data", "strategy"],
    )
    try:
        lease.acquire()
    except TaskLeaseBusyError as exc:
        _fail(key, task_id, str(exc))
        _release(key, task_id)
        return

    try:
        with PipelineProgress.bind(key, task_id) as prog:
            prog.mark_running()
            _duckdb_prepare()
            summary = runner(key, prog)
            if summary.get("success") is False:
                prog.fail(str(summary.get("error") or f"{label}未成功"))
            else:
                prog.complete(result=summary)
    except Exception as exc:  # noqa: BLE001
        logger.exception("%s failed key=%s task=%s", label, key, task_id)
        _fail(key, task_id, str(exc))
    finally:
        _duckdb_finalize()
        try:
            lease.release()
        except Exception:
            logger.exception("lease release failed task=%s", task_id)
        _release(key, task_id)


def _fail(key: str, task_id: str, message: str) -> None:
    inst = PipelineProgress.load(key, task_id)
    if inst is not None:
        inst.fail(message)


def _use_pipeline(prog: PipelineProgress, pipeline_name: str) -> None:
    """完整回测中途改进度名，后面的层才能推进同一条进度。"""
    prog._doc["pipeline_name"] = pipeline_name
    prog._doc["pipeline_description"] = PipelineProgress.pipeline_description(
        pipeline_name
    )
    prog._save()


def _run_enumerate(key: str, prog: PipelineProgress) -> Dict[str, Any]:
    _ = prog
    return _layer_summary(key, Strategy.enumerate(key), "enum")


def _run_price(key: str, prog: PipelineProgress) -> Dict[str, Any]:
    _ = prog
    return _layer_summary(key, Strategy.price_factor(key), "price")


def _run_portfolio(key: str, prog: PipelineProgress) -> Dict[str, Any]:
    _ = prog
    return _layer_summary(key, Strategy.portfolio(key), "portfolio")


def _run_simulate(key: str, prog: PipelineProgress) -> Dict[str, Any]:
    layers: Dict[str, Any] = {}
    for pipeline_name, step, fn in (
        ("enum", "enum", Strategy.enumerate),
        ("price", "price", Strategy.price_factor),
        ("portfolio", "portfolio", Strategy.portfolio),
    ):
        _use_pipeline(prog, pipeline_name)
        summary = _layer_summary(key, fn(key), step)
        layers[step] = summary
        if summary.get("success") is False:
            return {
                "key": key,
                "success": False,
                "error": f"{pipeline_name} 未成功",
                "layers": layers,
            }
    return {"key": key, "layers": layers}


def _run_attribute_enumerate(key: str, prog: PipelineProgress) -> Dict[str, Any]:
    _ = prog
    return _campaign_summary(key, Strategy.attribute_enumerate(key), "enum")


def _run_attribute_price(key: str, prog: PipelineProgress) -> Dict[str, Any]:
    _ = prog
    return _campaign_summary(key, Strategy.attribute_price(key), "price")


def _run_attribute_portfolio(key: str, prog: PipelineProgress) -> Dict[str, Any]:
    _ = prog
    return _campaign_summary(key, Strategy.attribute_portfolio(key), "portfolio")


def _run_rolling(key: str, prog: PipelineProgress) -> Dict[str, Any]:
    _ = prog
    return _campaign_summary(key, Strategy.rolling(key), "rolling")


def _layer_summary(key: str, result: Any, step: str) -> Dict[str, Any]:
    payload = result if isinstance(result, dict) else {}
    layer = payload.get(step) if isinstance(payload.get(step), dict) else payload
    summary: Dict[str, Any] = {
        "key": key,
        "step": step,
        "cache_hit": bool(payload.get("cache_hit")),
    }
    version_id = str(layer.get("version_id") or payload.get("version_id") or "").strip()
    if version_id:
        summary["version_id"] = version_id
    report = _relative(str(layer.get("output_dir") or ""))
    if not report and version_id:
        report = f"strategies/{key}/results/simulations/{version_id}"
    if report:
        summary["report_path"] = report
    if layer.get("success") is False or payload.get("success") is False:
        summary["success"] = False
    return summary


def _campaign_summary(key: str, result: Any, step: str) -> Dict[str, Any]:
    payload = result if isinstance(result, dict) else {}
    summary: Dict[str, Any] = {"key": key, "step": step}
    group_id = str(payload.get("group_id") or "").strip()
    if group_id:
        summary["group_id"] = group_id
    headline = payload.get("headline")
    if isinstance(headline, str) and headline.strip():
        summary["headline"] = headline.strip()
    report = _relative(str(payload.get("report_path") or payload.get("task_dir") or ""))
    if report:
        summary["report_path"] = report
    if payload.get("success") is False:
        summary["success"] = False
    return summary


def _relative(output_dir: str) -> str:
    text = str(output_dir or "").strip()
    if not text:
        return ""
    userspace = ProjectContext.path.get_userspace_root().resolve()
    try:
        return Path(text).resolve().relative_to(userspace).as_posix()
    except (OSError, ValueError):
        return ""


def _duckdb_prepare() -> None:
    try:
        from core.infra.db import Db

        pool = Db.duckdb.worker_pool
        if pool.is_backend():
            pool.recover_after_interrupt()
    except Exception as exc:
        logger.warning("DuckDB prepare: %s", exc)


def _duckdb_finalize() -> None:
    try:
        from core.infra.db import Db

        pool = Db.duckdb.worker_pool
        if not pool.is_backend():
            return
        pool.wait_pool_children_done(timeout_sec=30.0)
        from core.modules.data_manager import DataManager

        DataManager.ensure_restored_after_worker_pool()
    except Exception as exc:
        logger.warning("DuckDB finalize: %s", exc)
