"""SeriesRelation Facade。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from core.infra.project_context import ProjectContext
from core.modules.series_relation.core.constants import MAX_SERIES
from core.modules.series_relation.core.discovery.discovered import DiscoveredRelation
from core.modules.series_relation.core.discovery.discovery_service import DiscoveryService
from core.modules.series_relation.core.pipeline.runner import run_relation
from core.modules.series_relation.core.settings.relation_settings import validate_settings


class SeriesRelation:
    """多序列并置比较门面。"""

    MAX_SERIES = MAX_SERIES

    @staticmethod
    def list_infos() -> List[DiscoveredRelation]:
        return DiscoveryService.discover(
            declaration_lookup=SeriesRelation._declaration_lookup()
        )

    @staticmethod
    def list_keys() -> List[str]:
        return [item.key for item in SeriesRelation.list_infos()]

    @staticmethod
    def find(key_or_id: str) -> Optional[DiscoveredRelation]:
        return DiscoveryService.find(
            key_or_id,
            declaration_lookup=SeriesRelation._declaration_lookup(),
        )

    @staticmethod
    def validate(settings: Mapping[str, Any]) -> Dict[str, Any]:
        """返回 ``{ok, settings|None, errors}``。"""
        normalized, errors = validate_settings(
            settings,
            declaration_lookup=SeriesRelation._declaration_lookup(),
        )
        return {
            "ok": not errors and normalized is not None,
            "settings": normalized,
            "errors": errors,
        }

    @staticmethod
    def run(key_or_id: str) -> Dict[str, Any]:
        """发现场景并写入 ``results/``。"""
        info = SeriesRelation.find(key_or_id)
        if info is None:
            return {
                "success": False,
                "error": f"未找到 series_relation: {key_or_id}",
            }
        out = ProjectContext.path.get_series_relation_results_directory(
            info.relative_path
        )
        try:
            return run_relation(info.settings, output_dir=Path(out))
        except Exception as exc:
            return {"success": False, "key": info.key, "error": str(exc)}

    @staticmethod
    def _declaration_lookup():
        def lookup(data_key: str) -> Optional[Mapping[str, Any]]:
            try:
                from core.modules.data_contract import ContractIssuer
                from core.infra.project_context import ProjectContext as PC

                issuer = ContractIssuer()
                issuer.discover(user_space_path=PC.path.get_data_contract_root())
                if not issuer.is_available(data_key):
                    # try class cache after issue path
                    pass
                try:
                    return issuer.get_declaration(data_key)
                except Exception:
                    return None
            except Exception:
                return None

        return lookup


__all__ = ["SeriesRelation"]
