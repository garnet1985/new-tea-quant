"""Data source catalog for UI (read-only list)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_source import DataSourceManager
from core.modules.data_source.contracts import DataSourceConfig, UpdateMode
from core.modules.data_manager import DataManager

_RENEW_TYPE_LABELS: Dict[str, str] = {
    UpdateMode.INCREMENTAL.value: "增量",
    UpdateMode.ROLLING.value: "滚动",
    UpdateMode.REFRESH.value: "全量刷新",
}


def _renew_type_label(renew_type: str) -> str:
    key = str(renew_type or "").strip().lower()
    return _RENEW_TYPE_LABELS.get(key, key or "—")


def _resolve_display_name(source_key: str, mapping_info: Dict[str, Any]) -> str:
    custom = str((mapping_info or {}).get("display_name") or "").strip()
    if custom:
        return custom
    return DataSourceManager.default_display_names().get(source_key, source_key)


def _resolve_origin(source_key: str) -> str:
    return "system" if source_key in DataSourceManager.builtin_source_keys() else "userspace"


def _collect_provider_names(config: DataSourceConfig) -> List[str]:
    names = {
        str(api.provider_name).strip()
        for api in config.get_apis().values()
        if str(api.provider_name or "").strip()
    }
    return sorted(names)


def _summary(
    source_key: str,
    mapping_info: Dict[str, Any],
    config: DataSourceConfig,
    provider_classes: Dict[str, Any],
) -> Dict[str, Any]:
    providers = _collect_provider_names(config)
    auth = DataSourceManager.summarize_provider_auth(providers, provider_classes)
    renew_type = config.get_renew_mode().value
    renew_interval_days = config.get_over_time_threshold()
    rate_limit = DataSourceManager.min_rate_limit_per_minute(
        config.get_apis(), provider_classes
    )
    origin = _resolve_origin(source_key)
    can_renew = bool(auth["auth_ready"])

    return {
        "name": source_key,
        "display_name": _resolve_display_name(source_key, mapping_info),
        "target_table": config.get_table_name(),
        "is_enabled": bool((mapping_info or {}).get("is_enabled", True)),
        "depends_on": list((mapping_info or {}).get("depends_on") or []),
        "providers": providers,
        "providers_label": " / ".join(providers),
        "renew_type": renew_type,
        "renew_type_label": _renew_type_label(renew_type),
        "renew_interval_days": renew_interval_days,
        "rate_limit_per_minute": rate_limit,
        "requires_auth": bool(auth["requires_auth"]),
        "auth_ready": bool(auth["auth_ready"]),
        "missing_auth_providers": list(auth["missing_auth_providers"]),
        "auth_hint": str(auth["auth_hint"] or ""),
        "can_renew": can_renew,
        "origin": origin,
        "is_custom": origin == "userspace",
    }


def fetch_data_source_catalog_page(
    page: int,
    limit: int,
) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
    """Paginated data source catalog; ``page`` is 1-based, sorted by ``name``."""
    mgr = DataSourceManager(is_verbose=False)
    mappings = mgr.discover_mappings()
    provider_classes = DataSourceManager.discover_provider_classes()
    data_end = DataSourceManager.get_data_end_meta_light()

    ordered: List[Dict[str, Any]] = []
    for source_key in sorted(mappings.get_enabled().keys()):
        mapping_info = mappings.get_handler_info(source_key) or {}
        config = mgr.discover_config(source_key)
        if config is None:
            continue
        ordered.append(
            _summary(
                source_key,
                mapping_info,
                config,
                provider_classes,
            )
        )

    total = len(ordered)
    if total == 0:
        return [], 0, data_end

    page = max(1, int(page))
    limit = max(1, int(limit))
    start = (page - 1) * limit
    return ordered[start : start + limit], total, data_end


def fetch_data_source_freshness(
    source_names: Optional[List[str]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Lazy freshness for UI: DB last-update + ``renew_if_over_days`` vs ``data.json`` as-of.

    Returns ``({source_key: status_fields}, data_end)``.
    """
    mgr = DataSourceManager(is_verbose=False)
    mappings = mgr.discover_mappings()

    data_manager = DataManager.get_instance()
    if data_manager is None:
        data_manager = DataManager(is_verbose=False)
        data_manager.initialize()

    data_end = DataSourceManager.get_data_end_meta(data_manager)

    enabled_keys = sorted(mappings.get_enabled().keys())
    if source_names:
        wanted = {str(name).strip() for name in source_names if str(name).strip()}
        keys = [key for key in enabled_keys if key in wanted]
    else:
        keys = enabled_keys

    items: Dict[str, Dict[str, Any]] = {}
    for source_key in keys:
        config = mgr.discover_config(source_key)
        if config is None:
            continue
        update_status, update_status_label, update_status_hint = (
            DataSourceManager.evaluate_update_status(
                source_key=source_key,
                config=config,
                mappings=mappings,
                data_manager=data_manager,
            )
        )
        items[source_key] = {
            "update_status": update_status,
            "update_status_label": update_status_label,
            "update_status_hint": update_status_hint,
        }

    return items, data_end
