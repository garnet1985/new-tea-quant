"""Tag non_time_series 编排：轻量主进程一次计算（不进 BacktestEngine）。

消费者: Tag facade

流程:
  calc window → issue contracts → 一次 calculate_tag → flush / progress

落库 as_of 取计算窗 ``end_date``（无日历推进）。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.data_class.tag_definition import TagDefinition
from core.modules.tag.core.engines.global_based.constants import GLOBAL_ENTITY_ID
from core.modules.tag.core.engines.non_time_series.data_loader import (
    TagNonTimeSeriesDataLoader,
)
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

if TYPE_CHECKING:
    from core.modules.data_manager.core.data_services.stock.sub_services.tag_service import (
        TagDataService,
    )

logger = logging.getLogger(__name__)


class TagNonTimeSeriesPipeline:
    """non_time_series Tag：主进程一次性计算。"""

    @classmethod
    def run(
        cls,
        *,
        tag_info: DiscoveredTagInfo,
        scenario: Scenario,
        entity_ids: Optional[List[str]] = None,
        tag_data_service: Optional["TagDataService"] = None,
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
        as_of = run_end

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

        contracts = TagNonTimeSeriesDataLoader.load(
            settings,
            start_date=windows.data_start,
            end_date=windows.data_end,
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

        items = TagNonTimeSeriesDataLoader.to_items(contracts, as_of=as_of)
        base_key = settings.data.base_data_key
        base_rows = items.get(base_key) or []
        min_required = max(int(settings.data.min_required_records or 0), 0)
        if min_required and len(base_rows) < min_required:
            return {
                "success": True,
                "jobs": 1,
                "ok": 1,
                "fail": 0,
                "saved_tag_values": 0,
                "tag_values_count": 0,
                "message": (
                    f"base rows {len(base_rows)} < min_required_records={min_required}"
                ),
                "dry_run": dry_run,
                "entity_ids": [entity_id],
                "start_date": run_start,
                "end_date": run_end,
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

        tag_values: List[Dict[str, Any]] = []
        t0 = time.monotonic()
        fail = 0

        logger.info(
            "TagNonTimeSeriesPipeline start: scenario=%s entity=%s as_of=%s "
            "base_rows=%d dry_run=%s",
            scenario.name,
            entity_id,
            as_of,
            len(base_rows),
            dry_run,
        )

        if on_progress:
            on_progress(
                {
                    "phase": "non_time_series_start",
                    "as_of": as_of,
                    "base_rows": len(base_rows),
                }
            )

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

        if on_progress:
            on_progress(
                {
                    "phase": "non_time_series_done",
                    "as_of": as_of,
                    "tag_values_count": len(tag_values),
                    "saved_tag_values": saved,
                }
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
            "as_of": as_of,
        }

    @classmethod
    def _load_priors(
        cls,
        tag_data_service: Optional["TagDataService"],
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


__all__ = ["TagNonTimeSeriesPipeline"]
