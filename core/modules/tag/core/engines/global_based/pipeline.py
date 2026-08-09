"""Tag global 编排：轻量主进程推进（不进 BacktestEngine）。

消费者: Tag facade

流程:
  calc window → issue global contracts → 交易日历 as_of 循环
  → until 切片 → calculate_tag → flush / progress
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from core.modules.backtest_engine.contracts import Timeline
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.data_class.tag_definition import TagDefinition
from core.modules.tag.core.engines.global_based.constants import GLOBAL_ENTITY_ID
from core.modules.tag.core.engines.global_based.data_loader import TagGlobalDataLoader
from core.modules.tag.core.engines.shared.calc_window import (
    TagCalcWindowResolver,
)
from core.modules.tag.core.engines.shared.hooks.hook_params import TagContext
from core.modules.tag.core.engines.shared.hooks.runtime import TagHookRuntime
from core.modules.tag.core.engines.shared.prior_values import TagPriorValues
from core.modules.tag.core.engines.shared.services.tag_value_flush import (
    TagValueFlushService,
)
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import (
    TagSettings,
)
from core.modules.tag.core.enums import TagUpdateMode
from core.modules.tag.core.services.discovery.data.discovered_tag import DiscoveredTagInfo

logger = logging.getLogger(__name__)


class TagGlobalPipeline:
    """global 时序 Tag：主进程推进器。"""

    @classmethod
    def run(
        cls,
        *,
        tag_info: DiscoveredTagInfo,
        scenario: Scenario,
        entity_ids: Optional[List[str]] = None,
        tag_data_service: Optional[Any] = None,
        dry_run: bool = False,
        save_batch_size: int = 500,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        settings = TagSettings.from_dict(
            dict(scenario.settings or {}),
            tag_key=scenario.name,
        )
        settings.apply_defaults()

        ids = [str(e).strip() for e in (entity_ids or []) if str(e).strip()]
        if not ids:
            ids = [GLOBAL_ENTITY_ID]

        windows = TagCalcWindowResolver.resolve(
            scenario=scenario,
            settings=settings,
            entity_ids=ids,
            tag_data_service=tag_data_service,
        )
        if not windows.entities:
            return {
                "success": True,
                "jobs": 0,
                "ok": 0,
                "fail": 0,
                "saved_tag_values": 0,
                "tag_values_count": 0,
                "message": "no jobs",
                "dry_run": dry_run,
                "entity_ids": ids,
            }

        entity_window = windows.entities[0]
        entity_id = entity_window.entity_id
        run_start = entity_window.start_date
        run_end = entity_window.end_date

        hook_runtime, err = TagHookRuntime.from_tag_info(tag_info, settings)
        if err is not None or hook_runtime is None:
            return {
                "success": False,
                "jobs": 1,
                "ok": 0,
                "fail": 1,
                "saved_tag_values": 0,
                "tag_values_count": 0,
                "error": (err or {}).get("error") or "缺少hooks信息",
                "dry_run": dry_run,
                "entity_ids": ids,
            }

        try:
            points = list(
                Timeline.from_calendar_window(run_start, run_end).points or []
            )
        except Exception as exc:
            logger.error(
                "TagGlobalPipeline: 无法构建日历轴 %s—%s: %s",
                run_start,
                run_end,
                exc,
                exc_info=True,
            )
            return {
                "success": False,
                "jobs": 1,
                "ok": 0,
                "fail": 1,
                "saved_tag_values": 0,
                "tag_values_count": 0,
                "error": str(exc),
                "dry_run": dry_run,
                "entity_ids": ids,
            }

        contracts = TagGlobalDataLoader.load(
            settings, start_date=windows.data_start, end_date=windows.data_end
        )
        if settings.data.base_data_key not in contracts:
            return {
                "success": False,
                "jobs": 1,
                "ok": 0,
                "fail": 1,
                "saved_tag_values": 0,
                "tag_values_count": 0,
                "error": f"base contract 未加载: {settings.data.base_data_key}",
                "dry_run": dry_run,
                "entity_ids": ids,
            }

        prior_by_tag = cls._load_priors(
            tag_data_service, scenario=scenario, entity_id=entity_id
        )

        flush = TagValueFlushService(
            tag_data_service,
            dry_run=dry_run,
            batch_size=save_batch_size,
        )
        ctx_base = TagContext.assemble(
            tag_key=str(tag_info.key or scenario.name),
            settings=settings,
            entity_list=[entity_id],
            tag_path=str(
                getattr(tag_info, "unique_relative_path", None) or scenario.name
            ),
            entity_id=entity_id,
            entity_info={"id": entity_id},
            custom={},
        )

        min_required = max(int(settings.data.min_required_records or 0), 0)
        base_key = settings.data.base_data_key
        tag_values: List[Dict[str, Any]] = []
        t0 = time.monotonic()
        fail = 0

        logger.info(
            "TagGlobalPipeline start: scenario=%s entity=%s period=%s—%s "
            "points=%d dry_run=%s",
            scenario.name,
            entity_id,
            run_start,
            run_end,
            len(points),
            dry_run,
        )

        total_points = len(points)
        for index, point in enumerate(points):
            as_of = str(point or "").strip()
            if not as_of:
                continue
            if as_of < run_start or as_of > run_end:
                continue

            items = TagGlobalDataLoader.slice_items(contracts, as_of)
            base_rows = items.get(base_key) or []
            if min_required and len(base_rows) < min_required:
                continue

            for definition in scenario.tag_definitions:
                if not isinstance(definition, TagDefinition):
                    continue
                prior = None
                if definition.id is not None:
                    prior = prior_by_tag.get(str(int(definition.id)))
                if prior is None and definition.name:
                    prior = prior_by_tag.get(str(definition.name))
                scan_ctx = TagContext.fill(
                    ctx_base,
                    now=as_of,
                    items=items,
                    entity_id=entity_id,
                    entity_info={"id": entity_id},
                    tag_definition=definition,
                    prior_value=prior,
                )
                try:
                    result = hook_runtime.call("calculate_tag", scan_ctx)
                except Exception:
                    fail += 1
                    continue
                if not isinstance(result, dict):
                    continue
                value = result.get("value")
                if value is None:
                    continue
                tag_values.append(
                    {
                        "entity_id": entity_id,
                        "as_of_date": as_of,
                        "tag_definition_id": definition.id,
                        "tag_name": definition.name,
                        "value": value,
                        "start_date": result.get("start_date"),
                        "end_date": result.get("end_date"),
                    }
                )

            if on_progress and total_points and (index + 1) % 20 == 0:
                on_progress(
                    {
                        "phase": "global_tick",
                        "index": index + 1,
                        "total": total_points,
                        "as_of": as_of,
                        "tag_values_count": len(tag_values),
                    }
                )

        if tag_values:
            flush.extend(tag_values)
        saved = flush.flush()
        elapsed = time.monotonic() - t0
        success = fail == 0

        if (
            success
            and (not dry_run)
            and scenario.effective_update_mode() == TagUpdateMode.INCREMENTAL.value
            and tag_data_service is not None
            and run_end
        ):
            tag_data_service.mark_entity_calc_progress(
                scenario.name, {entity_id: run_end}
            )
            logger.info(
                "incremental progress saved: scenario=%s entity=%s end=%s",
                scenario.name,
                entity_id,
                run_end,
            )

        return {
            "success": success,
            "jobs": 1,
            "ok": 0 if fail else 1,
            "fail": fail,
            "tag_values_count": len(tag_values),
            "saved_tag_values": saved,
            "elapsed_seconds": elapsed,
            "dry_run": dry_run,
            "entity_ids": [entity_id],
            "start_date": run_start,
            "end_date": run_end,
        }

    @classmethod
    def _load_priors(
        cls,
        tag_data_service: Optional[Any],
        *,
        scenario: Scenario,
        entity_id: str,
    ) -> Dict[str, Any]:
        if tag_data_service is None:
            return {}
        def_ids = [
            int(d.id)
            for d in scenario.tag_definitions
            if getattr(d, "id", None) is not None
        ]
        if not def_ids:
            return {}
        batch = TagPriorValues.fetch_batch(
            tag_data_service,
            entity_ids=[entity_id],
            tag_definition_ids=def_ids,
        )
        raw = batch.get(entity_id) or {}
        out: Dict[str, Any] = {}
        for key, value in raw.items():
            out[str(key)] = TagPriorValues.parse_scalar(value)
        for definition in scenario.tag_definitions:
            if definition.id is None or not definition.name:
                continue
            sid = str(int(definition.id))
            if sid in out:
                out[str(definition.name)] = out[sid]
        return out


__all__ = ["TagGlobalPipeline"]
