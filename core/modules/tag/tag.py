"""Tag 模块 Facade — discovery / ensure / calculate。

本文件:
- Tag: 对外 API（execute / refresh / list）
  边界: 编排入口；不负责 BE 细节（委托 Pipeline）
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.modules.data_manager import DataManager
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.global_based import TagGlobalPipeline
from core.modules.tag.core.engines.per_entity.entity_based import TagEntityPipeline
from core.modules.tag.core.engines.per_entity.shared.tag_settings import TagSettings
from core.modules.tag.core.engines.per_entity.slice_based import TagSlicePipeline
from core.modules.tag.core.enums import TagExecutionMode
from core.modules.tag.core.services.discovery import DiscoveryService
from core.modules.tag.core.services.discovery.data.discovered_tag import (
    EnabledTagInfo,
    TagInfo,
)
from core.modules.tag.core.services.entity_list import TagEntityListResolver
from core.modules.tag.core.services.metadata_ensure import MetadataEnsureService

logger = logging.getLogger(__name__)


class Tag:
    """Tag 模块 Facade。"""

    def __init__(
        self,
        *,
        is_verbose: bool = False,
        dispatch_overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.is_verbose = bool(is_verbose)
        self._dispatch_overrides = dict(dispatch_overrides or {})
        self.data_mgr = DataManager()
        self.tag_data_service = self.data_mgr.stock.tags
        self._by_id: Dict[str, TagInfo] = {}
        self._by_key: Dict[str, TagInfo] = {}
        self.refresh()

    def refresh(self) -> None:
        """重新 discovery（含未启用）。"""
        self._by_id = {}
        self._by_key = {}
        for info in DiscoveryService.discover_tags():
            self._by_id[info.id()] = info
            if info.key:
                # 后发现的同 key 已被 discovery 跳过；此处仅索引
                self._by_key.setdefault(info.key, info)
            if self.is_verbose:
                logger.info(
                    "发现 Tag: id=%s key=%s enabled=%s",
                    info.id(),
                    info.key,
                    info.is_enabled,
                )

    def list_ids(self, *, enabled_only: bool = True) -> List[str]:
        """已发现 tag 的路径 id（相对 tags 根）。"""
        items = list(self._by_id.values())
        if enabled_only:
            items = [t for t in items if t.is_enabled]
        return sorted(t.id() for t in items)

    def list_keys(self, *, enabled_only: bool = True) -> List[str]:
        items = list(self._by_id.values())
        if enabled_only:
            items = [t for t in items if t.is_enabled]
        return sorted({t.key or t.id() for t in items})

    def find(self, key_or_id: str) -> Optional[TagInfo]:
        needle = str(key_or_id or "").strip()
        if not needle:
            return None
        if needle in self._by_id:
            return self._by_id[needle]
        if needle in self._by_key:
            return self._by_key[needle]
        return DiscoveryService.find_tag(needle)

    @staticmethod
    def _to_enabled(info: TagInfo) -> Optional[EnabledTagInfo]:
        if not info.is_enabled:
            return None
        enabled = DiscoveryService.get_enabled_tags([info])
        return enabled[0] if enabled else None

    def execute(
        self,
        scenario_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        *,
        tag_key: Optional[str] = None,
        on_pipeline_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        dry_run: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """执行 tag 计算。

        - ``settings`` + ``tag_key``：按内联 settings 跑（仍需 discovery 中的 hooks）
        - ``scenario_name``：按 meta.key 或路径
        - 都空：跑全部已启用
        """
        if settings is not None:
            key = str(tag_key or scenario_name or "").strip()
            if not key:
                logger.error("execute(settings=...) 需要 tag_key 或 scenario_name")
                return None
            return self._execute_inline_settings(
                settings,
                tag_key=key,
                on_progress=on_pipeline_progress,
                dry_run=dry_run,
            )

        if scenario_name:
            return self._execute_named(
                scenario_name,
                on_progress=on_pipeline_progress,
                dry_run=dry_run,
            )

        last: Optional[Dict[str, Any]] = None
        for info in DiscoveryService.get_enabled_tags(list(self._by_id.values())):
            last = self._execute_tag_info(
                info,
                on_progress=on_pipeline_progress,
                dry_run=dry_run,
            )
        return last

    def _execute_named(
        self,
        name_or_key: str,
        *,
        on_progress: Optional[Callable[[Dict[str, Any]], None]],
        dry_run: bool,
    ) -> Optional[Dict[str, Any]]:
        info = self.find(name_or_key)
        if info is None:
            logger.info("找不到场景: %s，跳过执行", name_or_key)
            return None
        enabled = self._to_enabled(info)
        if enabled is None:
            logger.info("场景 %s 未开启，跳过执行", info.id())
            return None
        return self._execute_tag_info(
            enabled, on_progress=on_progress, dry_run=dry_run
        )

    def _execute_inline_settings(
        self,
        settings: Dict[str, Any],
        *,
        tag_key: str,
        on_progress: Optional[Callable[[Dict[str, Any]], None]],
        dry_run: bool,
    ) -> Optional[Dict[str, Any]]:
        info = self.find(tag_key)
        if info is None:
            logger.error(
                "inline settings 需要已 discovery 的 tag（含 tag.py）: %s", tag_key
            )
            return None
        # 用调用方 settings 覆盖磁盘 settings，但保留 hooks 定位信息
        merged_info = TagInfo(
            unique_relative_path=info.unique_relative_path,
            tag_file=info.tag_file,
            settings_file=info.settings_file,
            folder=info.folder,
            key=info.key,
            display_name=info.display_name,
            is_enabled=bool(settings.get("is_enabled", info.is_enabled)),
            settings=dict(settings),
            hooks_class=info.hooks_class,
            hooks_module_path=info.hooks_module_path,
            hooks_class_name=info.hooks_class_name,
            hooks_file_path=info.hooks_file_path,
        )
        enabled = self._to_enabled(merged_info)
        if enabled is None:
            logger.info("场景 %s 未开启，跳过执行", info.id())
            return None
        return self._execute_tag_info(
            enabled, on_progress=on_progress, dry_run=dry_run
        )

    def _execute_tag_info(
        self,
        tag_info: EnabledTagInfo,
        *,
        on_progress: Optional[Callable[[Dict[str, Any]], None]],
        dry_run: bool,
    ) -> Optional[Dict[str, Any]]:
        tag_key = tag_info.id()
        ts = TagSettings.from_dict(dict(tag_info.settings or {}), tag_key=tag_key)
        report = ts.validate()
        if not report.is_usable():
            logger.error(
                "Tag settings 校验失败: %s errors=%s",
                tag_key,
                report.errors,
            )
            return None
        if not ts.is_enabled:
            logger.info("场景 %s 未开启，跳过执行", tag_key)
            return None

        scenario = Scenario.from_tag_settings(ts)
        effective_dry_run = bool(dry_run or ts.is_dry_run)
        scenario.is_dry_run = effective_dry_run
        if not self.tag_data_service:
            logger.error("无法获取 tag_data_service，跳过执行")
            return None
        MetadataEnsureService(self.tag_data_service).ensure(scenario)

        stock_limit = self._dispatch_overrides.get("stock_limit")
        entity_ids = TagEntityListResolver.resolve(
            scenario,
            stock_limit=int(stock_limit) if stock_limit is not None else None,
        )
        if not entity_ids:
            logger.info("无法获取实体列表，跳过执行: %s", tag_key)
            return None

        route = ts.data.base_route()
        run_kwargs = dict(
            tag_info=tag_info,
            scenario=scenario,
            entity_ids=entity_ids,
            tag_data_service=self.tag_data_service,
            dry_run=effective_dry_run,
            on_progress=on_progress,
        )

        if route == "global":
            result = TagGlobalPipeline.run(**run_kwargs)
            self._save_performance_report(result, scenario, tag_key, "global")
            return result

        if route == "non_time_series":
            logger.error(
                "Tag non_time_series 路由尚未实现，跳过: %s base=%s",
                tag_key,
                ts.data.base_data_key,
            )
            return None

        mode = scenario.execution_mode
        if mode == TagExecutionMode.SLICE_BASED.value:
            result = TagSlicePipeline.run(**run_kwargs)
            self._save_performance_report(result, scenario, tag_key, "slice_based")
            return result

        result = TagEntityPipeline.run(**run_kwargs)
        self._save_performance_report(result, scenario, tag_key, "entity_based")
        return result

    def _save_performance_report(
        self,
        result: Optional[Dict[str, Any]],
        scenario: Scenario,
        tag_key: str,
        execution_mode: str,
    ) -> None:
        if not result:
            return
        try:
            report = {
                "schema_version": 1,
                "report_kind": "tag_performance",
                "timestamp": datetime.now().isoformat(),
                "scenario_name": scenario.name,
                "tag_key": tag_key,
                "execution_mode": execution_mode,
                "summary": {
                    "wall_clock_seconds": round(
                        float(result.get("elapsed_seconds") or 0), 3
                    ),
                    "total_jobs": result.get("jobs", 0),
                    "ok_jobs": result.get("ok", 0),
                    "failed_jobs": result.get("fail", 0),
                    "tag_values_count": result.get("tag_values_count", 0),
                    "saved_tag_values": result.get("saved_tag_values", 0),
                    "dry_run": bool(result.get("dry_run")),
                },
            }
            tags_root = ProjectContext.path.get_tags_root()
            results_dir = Path(tags_root) / tag_key / "results" / "performance"
            results_dir.mkdir(parents=True, exist_ok=True)
            version = 1
            while (results_dir / str(version)).exists():
                version += 1
            version_dir = results_dir / str(version)
            version_dir.mkdir(parents=True, exist_ok=True)
            report_path = version_dir / "0_performance_report.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(
                "[%s] 性能报告已保存: %s (version=%d)",
                tag_key,
                report_path,
                version,
            )
        except Exception as exc:
            logger.warning("[%s] 保存性能报告失败: %s", tag_key, exc)


__all__ = ["Tag"]
