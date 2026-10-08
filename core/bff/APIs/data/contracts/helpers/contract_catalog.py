"""Data contract catalog for UI (read-only list + reload)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.infra.project_context import ProjectContext
from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import ContractScope, ContractType


def _origin_label(is_customized: bool) -> str:
    return "userspace" if is_customized else "system"


def _summary(key: str, declaration: Dict[str, Any]) -> Dict[str, Any]:
    meta = declaration.get("meta") or {}
    display_name = str(meta.get("display_name") or key).strip() or key
    ctype = str(meta.get("type") or "").strip().lower()
    scope = str(meta.get("scope") or "").strip().lower()
    origin = _origin_label(bool(declaration.get("_is_customized", False)))
    return {
        "key": key,
        "display_name": display_name,
        "is_time_series": ctype == ContractType.TIME_SERIES,
        "is_per_entity": scope == ContractScope.PER_ENTITY,
        "origin": origin,
        "is_custom": origin == "userspace",
    }


def _catalog_entries(*, force_reload: bool = False) -> List[Tuple[str, Dict[str, Any]]]:
    if force_reload or not ContractIssuer._discovered:
        ContractIssuer.reload(
            user_space_path=ProjectContext.path.get_data_contract_root()
        )
    entries = [
        (key, declaration)
        for key, declaration in ContractIssuer._declarations_cache.items()
    ]
    entries.sort(key=lambda item: item[0])
    return entries


def reload_data_contract_catalog() -> Dict[str, Any]:
    """强制重新发现并刷新类级注册表；返回摘要供 UI。"""
    total = ContractIssuer.reload(
        user_space_path=ProjectContext.path.get_data_contract_root()
    )
    return {"total": int(total)}


def fetch_data_contract_catalog_page(
    page: int, limit: int, *, force_reload: bool = False
) -> Tuple[List[Dict[str, Any]], int]:
    """Paginated data contract catalog; ``page`` is 1-based, sorted by ``key``."""
    ordered = _catalog_entries(force_reload=force_reload)
    total = len(ordered)
    if total == 0:
        return [], 0

    page = max(1, int(page))
    limit = max(1, int(limit))
    start = (page - 1) * limit
    chunk = ordered[start : start + limit]
    return [_summary(key, decl) for key, decl in chunk], total
