"""ScannerJobExecutor — 单日轴 lookback 加载 + scan hooks。

本文件:
- ScannerJobExecutor: RunCallbacks 面；on_tick 调 scan_opportunity、贴板标注
  边界: 负责 worker 内 scan 业务；不负责 Pipeline 缓存/adapters、BE batch 切分
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.data_contract import DATA_KEY
from core.modules.strategy.core.engines.scanner.helpers.tradability import (
    annotate_enter_at_limit,
)
from core.modules.strategy.core.engines.scanner.job_builder import ScannerJobBuilder
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
    JobBundleLoader,
)
from core.modules.strategy.core.engines.shared.services.as_of_slice import AsOfSlice
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.hook_params import StrategyContext
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime

logger = logging.getLogger(__name__)

_CTX_KEY = "_scanner_runtime"


class ScannerJobExecutor:
    """扫描 worker 钩子面。

    边界:
    - 负责: 装载 lookback contracts、调用 scan hooks、回传 opportunities
    - 不负责: 调度 / 切 batch（BE）、cache / adapters（Pipeline）
    """

    task_log_label = "scanner task"

    @classmethod
    def build_run_callbacks(cls) -> RunCallbacks:
        return RunCallbacks(
            on_before_all_tasks_start=cls.on_before_all_tasks_start,
            on_before_task_start=cls.on_before_task_start,
            on_after_task_complete=cls.on_after_task_complete,
            on_after_all_tasks_complete=cls.on_after_all_tasks_complete,
            on_task_result=cls.on_task_result,
            on_tick=cls.on_tick,
            on_ticks_complete=cls.on_ticks_complete,
        )

    @classmethod
    def on_before_all_tasks_start(cls, plan: Any, batches: List[Any]) -> None:
        print(
            f"  扫描调度: {len(batches)} batches, "
            f"workers={getattr(plan, 'max_workers', '?')}",
            flush=True,
        )

    @classmethod
    def on_before_task_start(cls, job_context: Any) -> Dict[str, Any]:
        payload = job_context.payload or {}
        meta = ScannerJobBuilder.scanner_meta(payload)
        scan_date = str(meta.get("scan_date") or "").strip()
        settings_raw = payload.get("settings") if isinstance(payload, dict) else {}
        settings = (
            StrategySettings.from_dict(dict(settings_raw))
            if isinstance(settings_raw, dict)
            else StrategySettings.from_dict({})
        )
        settings.apply_defaults()

        hook_runtime, err = StrategyHookRuntime.from_strategy_info(
            payload.get("strategy_info") or {},
            settings,
        )
        if hook_runtime is None:
            logger.error("scanner 加载 hooks 失败: %s", err)
            return {
                "entity_contracts": {},
                "global_data": {},
                _CTX_KEY: {
                    "scan_date": scan_date,
                    "settings": settings,
                    "hook_runtime": None,
                    "opportunities": [],
                    "error": err,
                },
            }

        loaded = JobBundleLoader.load(payload)
        entity_ids = [
            str(item.get("id") or "").strip()
            for item in (payload.get("entity_specified") or [])
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ]
        stock_info = {eid: StockMetaHelper.load(eid) for eid in entity_ids}
        strategy_name = str(
            getattr(hook_runtime, "strategy_name", "")
            or (payload.get("strategy_info") or {}).get("key")
            or ""
        ).strip()

        scan_contexts: Dict[str, StrategyContext] = {}
        for eid in entity_ids:
            ctx = StrategyContext.assemble(
                strategy_key=strategy_name,
                settings=settings,
                stock_list=[eid],
                entity_id=eid,
                entity_info={"id": eid, **stock_info.get(eid, {})},
            )
            scan_contexts[eid] = ctx

        return {
            **loaded,
            _CTX_KEY: {
                "scan_date": scan_date,
                "settings": settings,
                "hook_runtime": hook_runtime,
                "market_profile": str(meta.get("market_profile") or "").strip(),
                "stock_info": stock_info,
                "scan_contexts": scan_contexts,
                "opportunities": [],
                "scanned": False,
            },
        }

    @classmethod
    def on_tick(cls, job_context: Any, point: str, index: int) -> None:
        """推进时间(point) → 切数据 → 执行业务。"""
        _ = index
        init = job_context.init if isinstance(job_context.init, dict) else {}
        runtime = init.get(_CTX_KEY)
        if not isinstance(runtime, dict):
            return
        if runtime.get("scanned"):
            return
        hook_runtime = runtime.get("hook_runtime")
        if hook_runtime is None:
            runtime["scanned"] = True
            return

        as_of = str(point or "").strip()  # 唯一时钟：BE Timeline 传入的 point
        entity_contracts = init.get("entity_contracts") or {}
        global_data = init.get("global_data") or {}
        settings = runtime.get("settings")
        base_key = (
            settings.data.base_data_key
            if settings is not None
            else DATA_KEY.STOCK_KLINE_DAILY
        )
        market_profile = str(runtime.get("market_profile") or "").strip()
        st_provider = entity_contracts.get(DATA_KEY.STOCK_ST_PERIODS)

        # —— 切数据 ——
        sliced_by_entity = AsOfSlice.slice_contracts(entity_contracts, as_of)
        out: List[Opportunity] = runtime.setdefault("opportunities", [])

        # —— 执行业务 ——
        for eid, base_ctx in (runtime.get("scan_contexts") or {}).items():
            per_entity = sliced_by_entity.get(eid) or {}
            complete = {**global_data, **per_entity} if global_data else dict(per_entity)
            try:
                scan_ctx = StrategyContext.fill(
                    base_ctx,
                    now=as_of,
                    items=complete,
                    entity_id=eid,
                    entity_info=base_ctx.data.entity_info,
                )
            except Exception as exc:
                logger.error(
                    "scanner StrategyContext.fill 失败 entity=%s: %s",
                    eid,
                    exc,
                    exc_info=True,
                )
                continue

            try:
                hook_runtime.call_if_overridden("on_before_scan", scan_ctx)
                scanned = hook_runtime.call("scan_opportunity", scan_ctx)
            except Exception as exc:
                logger.error(
                    "scanner hooks 失败 entity=%s: %s",
                    eid,
                    exc,
                    exc_info=True,
                )
                continue

            opportunity: Optional[Opportunity] = None
            if isinstance(scanned, Opportunity):
                opportunity = scanned
                stock_info = (runtime.get("stock_info") or {}).get(eid, {"id": eid})
                opportunity.bind_scan_context(
                    strategy_key=str(hook_runtime.strategy_name or ""),
                    stock_id=eid,
                    stock_info=stock_info,
                    trigger_date=as_of,
                    market_profile=market_profile or None,
                )
                opportunity.stamp_status_at_trigger(
                    status_tags_provider=st_provider,
                    trade_date=as_of,
                )
                klines = complete.get(base_key) or []
                if not isinstance(klines, list):
                    klines = []
                annotate_enter_at_limit(
                    opportunity,
                    market_profile=market_profile,
                    klines=klines,
                    scan_date=as_of,
                )
                out.append(opportunity)

            try:
                after_ctx = StrategyContext.fill(
                    base_ctx,
                    now=as_of,
                    items=complete,
                    opportunity=opportunity,
                    entity_id=eid,
                    entity_info=base_ctx.data.entity_info,
                )
                hook_runtime.call_if_overridden("on_after_scan", after_ctx)
            except Exception as exc:
                logger.error(
                    "on_after_scan 失败 entity=%s: %s",
                    eid,
                    exc,
                    exc_info=True,
                )

        runtime["scanned"] = True

    @classmethod
    def on_ticks_complete(cls, job_context: Any, timeline: Any) -> Dict[str, Any]:
        _ = timeline
        init = job_context.init if isinstance(job_context.init, dict) else {}
        runtime = init.get(_CTX_KEY) if isinstance(init.get(_CTX_KEY), dict) else {}
        opportunities = list(runtime.get("opportunities") or [])
        return {
            "success": runtime.get("error") is None,
            "opportunities": [opp.to_dict() for opp in opportunities],
            "opportunities_count": len(opportunities),
            "error": runtime.get("error"),
        }

    @classmethod
    def on_after_task_complete(cls, job_context: Any) -> None:
        _ = job_context

    @classmethod
    def on_after_all_tasks_complete(cls, job_reports: List[Any]) -> None:
        logger.info("scanner 全部 task 完成：total=%d", len(job_reports))

    @classmethod
    def on_task_result(cls, report: Any, progress: Any) -> None:
        logger.info(
            "scanner 进度：%s/%s (ok=%s, fail=%s) job_id=%s success=%s",
            progress.finished,
            progress.total,
            progress.ok,
            progress.fail,
            report.job_id,
            report.success,
        )


__all__ = ["ScannerJobExecutor"]
