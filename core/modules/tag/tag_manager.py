"""
Tag Manager - 统一管理所有业务场景（Scenario）

唯一执行入口：`execute()` → timeline / sliced 引擎。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.data_manager import DataManager
from core.modules.tag.config import get_scenarios_root
from core.modules.tag.engines.shared.base_worker import BaseTagWorker
from core.modules.tag.engines.sliced.pipeline import run_sliced_pipeline
from core.modules.tag.engines.timeline.pipeline import run_timeline_pipeline
from core.modules.tag.enums import TagExecutionMode, TagTargetType
from core.modules.tag.models.scenario_model import ScenarioModel
from core.modules.tag.services.discovery import TagDiscoveryHelper

logger = logging.getLogger(__name__)


class TagManager:
    """Tag Manager - 发现 scenario 并执行 tag 计算。"""

    def __init__(self, is_verbose=False, dispatch_overrides: Optional[Dict[str, Any]] = None):
        self.is_verbose = is_verbose
        self._dispatch_overrides = dict(dispatch_overrides or {})
        self.data_mgr = DataManager()
        self.tag_data_service = self.data_mgr.stock.tags
        self._contract_cache = ContractCacheManager()
        self._data_contract_manager = DataContractManager(contract_cache=self._contract_cache)
        self.scenario_cache: Dict[str, Dict[str, Any]] = {}
        self.entity_list_cache: Dict[str, List[str]] = {}
        self._discover_scenarios_from_folder()

    def refresh_scenario(self) -> None:
        self._clear_cache()
        self._discover_scenarios_from_folder()

    def execute(
        self,
        scenario_name: str | None = None,
        settings: Dict[str, Any] | None = None,
        *,
        tag_key: str | None = None,
    ) -> None:
        if settings is not None:
            key = str(tag_key or scenario_name or "inline").strip()
            scenario_model = ScenarioModel.create_from_settings(settings, tag_key=key)
            if not scenario_model:
                logger.info("创建场景模型失败，跳过执行")
                return
            self._run_scenario(scenario_model, tag_key=key)
            return
        if scenario_name:
            self._execute_named(scenario_name)
            return
        for name in self.scenario_cache:
            self._execute_named(name)

    def _execute_named(self, name_or_key: str) -> None:
        tag_key = self._resolve_tag_key(name_or_key)
        if not tag_key:
            logger.info("找不到场景: %s，跳过执行", name_or_key)
            return
        scenario_cache = self.scenario_cache.get(tag_key)
        if not scenario_cache:
            logger.info("找不到场景: %s，跳过执行", name_or_key)
            return
        scenario_model = ScenarioModel.create_from_settings(
            scenario_cache.get("settings", {}),
            tag_key=tag_key,
        )
        if not scenario_model:
            return
        self._run_scenario(scenario_model, tag_key=tag_key)

    def _run_scenario(self, scenario_model: ScenarioModel, *, tag_key: str) -> None:
        if not scenario_model.is_enabled():
            logger.info("场景 %s 未开启，跳过执行", scenario_model.get_name())
            return

        tag_data_service = self.data_mgr.stock.tags
        if not tag_data_service:
            logger.error("无法获取 tag_data_service，跳过执行")
            return
        scenario_model.ensure_metadata(tag_data_service)

        settings = scenario_model.get_settings()
        entity_list = self._resolve_entity_list(scenario_model, settings)
        if not entity_list:
            logger.info("无法获取实体列表，跳过执行")
            return

        stock_limit = self._dispatch_overrides.get("stock_limit")
        if stock_limit is not None and len(entity_list) > int(stock_limit):
            logger.warning(
                "实体列表截断 %d → %d（stock_limit）",
                len(entity_list),
                int(stock_limit),
            )
            entity_list = entity_list[: int(stock_limit)]

        worker_class = self._get_worker_class(tag_key)
        if worker_class is None:
            logger.error("无法获取 worker_class，跳过执行: tag_key=%s", tag_key)
            return

        if scenario_model.get_execution_mode() == TagExecutionMode.CALENDAR_SLICE:
            run_sliced_pipeline(
                self,
                scenario_model=scenario_model,
                entity_list=entity_list,
                settings=settings,
                tag_key=tag_key,
            )
            return

        run_timeline_pipeline(
            self,
            scenario_model=scenario_model,
            entity_list=entity_list,
            settings=settings,
            worker_class=worker_class,
            tag_key=tag_key,
        )

    def _resolve_entity_list(
        self, scenario_model: ScenarioModel, settings: Dict[str, Any]
    ) -> List[str]:
        tag_target_type = str(settings.get("tag_target_type") or "").strip().lower()
        if tag_target_type == TagTargetType.GENERAL.value:
            return ["__general__"]
        return self._get_entity_list(scenario_model)

    def _discover_scenarios_from_folder(self) -> None:
        discovered = TagDiscoveryHelper.discover_tags(get_scenarios_root())
        scenario_cache: Dict[str, Dict[str, Any]] = {}
        for tag_key, item in discovered.items():
            scenario_cache[tag_key] = {
                "tag_key": tag_key,
                "name": item.settings_name,
                "scenario_folder_path": tag_key,
                "settings": item.settings,
                "settings_file_path": item.folder / "settings.py",
                "worker_class": item.worker_class,
                "worker_file_path": str(item.worker_file_path),
                "worker_module_path": item.worker_module_path,
                "worker_class_name": item.worker_class_name,
            }
            if self.is_verbose:
                logger.info("发现可用场景: tag_key=%s, settings.name=%s", tag_key, item.settings_name)
        self.scenario_cache = scenario_cache

    def _resolve_tag_key(self, name_or_key: str) -> Optional[str]:
        key = str(name_or_key or "").strip()
        if not key:
            return None
        if key in self.scenario_cache:
            return key
        matches = [
            tag_key
            for tag_key, cache in self.scenario_cache.items()
            if str((cache.get("settings") or {}).get("name") or "") == key
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            logger.warning(
                "settings.name=%r 对应多个 tag 路径: %s，请使用完整 tag_key",
                key,
                ", ".join(matches),
            )
        return None

    def _get_worker_class(self, tag_key: str) -> Optional[Type[BaseTagWorker]]:
        cache = self.scenario_cache.get(tag_key)
        if cache:
            return cache.get("worker_class")
        logger.warning("Tag 场景 %s 不在 cache 中，无法获取 worker_class", tag_key)
        return None

    def _get_entity_list(self, scenario_model: ScenarioModel) -> List[str]:
        settings = scenario_model.get_settings()
        declarations = (settings.get("data") or {}).get("required") or []
        per_entity_data_id = self._pick_primary_per_entity_data_id(declarations)
        if per_entity_data_id is None:
            logger.warning("当前场景无 PER_ENTITY 数据源，无法构建 entity 列表")
            return []

        cache_key = f"per_entity:{per_entity_data_id}"
        if cache_key in self.entity_list_cache:
            return self.entity_list_cache[cache_key]

        spec = self._data_contract_manager.map.get(per_entity_data_id) or {}
        list_data_id = spec.get("entity_list_data_id")
        if not isinstance(list_data_id, DataKey):
            logger.warning(
                "data_id=%s 未注册 entity_list_data_id，无法推导实体列表",
                per_entity_data_id.value,
            )
            return []

        list_contract = self._data_contract_manager.issue(list_data_id).require_contract()
        list_rows = list(list_contract.data or [])
        list_spec = self._data_contract_manager.map.get(list_data_id) or {}
        keys = list_spec.get("unique_keys") or ["id"]
        id_field = str(keys[0]) if keys else "id"
        entity_list = [row.get(id_field) for row in list_rows if row.get(id_field)]
        self.entity_list_cache[cache_key] = entity_list
        return entity_list

    def _pick_primary_per_entity_data_id(self, declarations: List[Dict[str, Any]]) -> Optional[DataKey]:
        for item in declarations:
            raw = str(item.get("data_id") or "").strip()
            if not raw:
                continue
            try:
                dk = DataKey(raw)
            except ValueError:
                continue
            spec = self._data_contract_manager.map.get(dk)
            if spec and spec.get("scope") == ContractScope.PER_ENTITY:
                return dk
        return None

    def _clear_cache(self) -> None:
        self.scenario_cache = {}
        self.entity_list_cache = {}
