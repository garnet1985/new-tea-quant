"""Tag job stage：在 worker 内装填 kline/prior 等，写入 payload _inject。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.tag.engines.shared.data.tag_data_manager import TagDataManager
from core.modules.tag.engines.shared.staging.batch_stage import stage_entities_batch
from core.modules.tag.engines.shared.staging.prior_values import fetch_prior_tag_values

if TYPE_CHECKING:
    from core.modules.data_manager import DataManager


@dataclass(frozen=True)
class TagStageJob:
    job_id: str
    payload: Dict[str, Any]


class TagJobStager:
    """主进程 Tag 装填器（IO → inline inject bundle）。"""

    def __init__(
        self,
        *,
        data_mgr: "DataManager",
        contract_cache: Optional[ContractCacheManager] = None,
    ) -> None:
        self._data_mgr = data_mgr
        self._contract_cache = contract_cache or ContractCacheManager()

    def stage_job(self, job: TagStageJob) -> TagStageJob:
        payload = dict(job.payload)
        entities = payload.get("entities")
        if isinstance(entities, list) and len(entities) > 1:
            return self._to_executable_batch(job, payload, entities)
        if isinstance(entities, list) and len(entities) == 1:
            return self._to_executable_single(job, self._single_payload_from_batch(payload, entities[0]))
        return self._to_executable_single(job, payload)

    def _to_executable_batch(
        self,
        job: TagStageJob,
        payload: Dict[str, Any],
        entities: List[Dict[str, Any]],
    ) -> TagStageJob:
        settings = dict(payload.get("settings") or {})
        tag_def_ids = [
            int(item["id"])
            for item in (payload.get("tag_definitions") or [])
            if item.get("id") is not None
        ]
        by_entity = stage_entities_batch(
            data_mgr=self._data_mgr,
            entities=entities,
            settings=settings,
            tag_definition_ids=tag_def_ids,
        )
        worker_payload = self._build_shared_worker_payload(payload)
        worker_payload["entities"] = list(entities)
        worker_payload["_inject"] = {"batch": True, "by_entity": by_entity}
        return TagStageJob(job_id=job.job_id, payload=worker_payload)

    def _to_executable_single(self, job: TagStageJob, payload: Dict[str, Any]) -> TagStageJob:
        entity_id = str(payload.get("entity_id") or "")
        entity_type = str(payload.get("entity_type") or "stock")
        scenario_name = str(payload.get("scenario_name") or "")
        settings = dict(payload.get("settings") or {})
        start_date = str(payload.get("start_date") or "")
        end_date = str(payload.get("end_date") or "")

        tag_data_manager = TagDataManager(
            entity_id=entity_id,
            entity_type=entity_type,
            scenario_name=scenario_name,
            settings=settings,
            data_mgr=self._data_mgr,
            contract_cache=self._contract_cache,
            global_extra_cache=payload.get("global_extra_cache") or {},
        )
        tag_data_manager.hydrate_row_slots(start_date, end_date)
        trading_dates = tag_data_manager.get_trading_dates(start_date, end_date)
        slot_data = tag_data_manager.get_slot_data()
        time_field_overrides = tag_data_manager.get_time_field_overrides()
        tag_def_ids = [
            int(item["id"])
            for item in (payload.get("tag_definitions") or [])
            if item.get("id") is not None
        ]
        prior_tag_values = fetch_prior_tag_values(
            self._data_mgr.stock.tags,
            entity_id=entity_id,
            tag_definition_ids=tag_def_ids,
        )

        worker_payload = self._build_worker_payload(
            payload,
            slot_data=slot_data,
            trading_dates=trading_dates,
            time_field_overrides=time_field_overrides,
            prior_tag_values=prior_tag_values,
        )
        return TagStageJob(job_id=job.job_id, payload=worker_payload)

    @staticmethod
    def _single_payload_from_batch(payload: Dict[str, Any], entity: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(payload)
        merged.update(entity)
        merged.pop("entities", None)
        return merged

    @staticmethod
    def _build_shared_worker_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        keys = (
            "entity_type",
            "scenario_name",
            "update_mode",
            "tag_definitions",
            "settings",
            "worker_module_path",
            "worker_class_name",
            "worker_file_path",
            "global_extra_cache",
        )
        return {key: payload[key] for key in keys if key in payload}

    @staticmethod
    def _build_worker_payload(
        source_payload: Dict[str, Any],
        *,
        slot_data: Dict[str, List[Dict[str, Any]]],
        trading_dates: List[str],
        time_field_overrides: Dict[str, Optional[str]],
        prior_tag_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        keys = (
            "entity_id",
            "entity_type",
            "scenario_name",
            "update_mode",
            "start_date",
            "end_date",
            "tag_definitions",
            "settings",
            "worker_module_path",
            "worker_class_name",
            "worker_file_path",
        )
        worker_payload = {key: source_payload[key] for key in keys if key in source_payload}
        worker_payload["global_extra_cache"] = source_payload.get("global_extra_cache") or {}
        worker_payload["_inject"] = {
            "trading_dates": list(trading_dates),
            "time_field_overrides": dict(time_field_overrides),
            "slot_data": {k: list(v or []) for k, v in slot_data.items()},
            "prior_tag_values": dict(prior_tag_values or {}),
        }
        return worker_payload
