"""跨模块 ``cli.py list <resource>`` catalog。

resource 带域前缀（如 ``stock.area``），避免全局撞名。
各域查询走对应模块公开 API；本文件只做编排与展示。
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# stock.* → DataManager.stock.list.load_filter_options 的维度名
_STOCK_FILTER_RESOURCES: Dict[str, str] = {
    "stock.area": "area",
    "stock.industry": "industry",
    "stock.board": "board",
    "stock.market": "market",
    "stock.list_status": "list_status",
}

_STOCK_GROUP = "stock"

# 静态 resource → loader（返回 items 列表）
_STATIC_LOADERS: Dict[str, Callable[[], List[Dict[str, Any]]]] = {}


def _register_static() -> None:
    if _STATIC_LOADERS:
        return
    _STATIC_LOADERS.update(
        {
            "datakey": _load_datakeys,
            "tag": _load_tags,
            "strategy": _load_strategies,
            "indicator": _load_indicators,
            "table": _load_tables,
        }
    )


def known_resources() -> List[str]:
    """已注册静态 resource（不含动态 ``tag.<id>``）。"""
    _register_static()
    return sorted(set(_STOCK_FILTER_RESOURCES) | set(_STATIC_LOADERS))


def resource_help_lines() -> List[str]:
    _register_static()
    lines = [
        "用法: python cli.py list <resource>",
        "      python cli.py ls <resource>",
        "",
        "股票池维度（settings.data.stock_list_filter）:",
    ]
    for name in sorted(_STOCK_FILTER_RESOURCES):
        dim = _STOCK_FILTER_RESOURCES[name]
        lines.append(f"  {name:<22} → filter 键 {dim}")
    lines.extend(
        [
            "  stock                  → 一次列出全部股票池维度",
            "",
            "其它:",
            "  datakey                → data_key（type / scope）",
            "  tag                    → 已发现的 tag 场景",
            "  tag.<key>              → 某 tag 的 tag_definitions（推荐 meta.key；也可用路径 id）",
            "  strategy               → 已发现策略（key / is_enabled / name / id）",
            "  indicator              → 可用技术指标名",
            "  table                  → 已注册逻辑表名",
            "",
            "例: python cli.py list datakey --json",
            "    python cli.py list tag.market_cap_tier",
            "    python cli.py list strategy",
        ]
    )
    return lines


def run(resource: Optional[str], *, as_json: bool = False) -> int:
    """执行 list；成功 0，未知 resource 1。"""
    _register_static()
    key = str(resource or "").strip()
    if not key:
        for line in resource_help_lines():
            print(line, flush=True)
        return 0

    if key == _STOCK_GROUP:
        payload = _load_stock_options(dim=None)
        _print_grouped(payload, as_json=as_json, title="stock.*")
        return 0

    if key in _STOCK_FILTER_RESOURCES:
        dim = _STOCK_FILTER_RESOURCES[key]
        payload = _load_stock_options(dim=dim)
        _print_grouped(payload, as_json=as_json, title=key)
        return 0

    if key in _STATIC_LOADERS:
        items = _STATIC_LOADERS[key]()
        _print_items(key, items, as_json=as_json)
        return 0

    if key.startswith("tag.") and len(key) > 4:
        tag_id = key[4:]
        items, err = _load_tag_definitions(tag_id)
        if err:
            print(err, flush=True)
            return 1
        _print_items(key, items, as_json=as_json)
        return 0

    print(f"未知 resource: {key}", flush=True)
    print(flush=True)
    for line in resource_help_lines():
        print(line, flush=True)
    return 1


def _load_stock_options(dim: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    from core.modules.data_manager import DataManager

    return DataManager().stock.list.load_filter_options(dim)


def _load_datakeys() -> List[Dict[str, Any]]:
    from core.infra.project_context import ProjectContext
    from core.modules.data_contract import ContractIssuer

    issuer = ContractIssuer()
    issuer.discover(user_space_path=ProjectContext.path.get_data_contract_root())
    rows: List[Dict[str, Any]] = []
    for data_key in sorted(issuer.list_available_keys()):
        decl = issuer.get_declaration(data_key)
        meta = decl.get("meta") if isinstance(decl.get("meta"), dict) else {}
        ctype = str(meta.get("type") or "").strip()
        scope = str(meta.get("scope") or "").strip()
        rows.append(
            {
                "key": data_key,
                "type": ctype,
                "scope": scope,
                "time_series": ctype == "time_series",
                "per_entity": scope == "per_entity",
                "display_name": str(meta.get("display_name") or "").strip(),
            }
        )
    return rows


def _load_tags() -> List[Dict[str, Any]]:
    from core.modules.tag import Tag

    tag = Tag()
    rows: List[Dict[str, Any]] = []
    for tid in tag.list_ids(enabled_only=False):
        info = tag.find(tid)
        if info is None:
            rows.append(
                {"key": "", "is_enabled": False, "name": "", "id": tid}
            )
            continue
        rows.append(
            {
                "key": str(getattr(info, "key", "") or "").strip(),
                "is_enabled": bool(getattr(info, "is_enabled", False)),
                "name": str(getattr(info, "display_name", "") or "").strip(),
                "id": tid,
            }
        )
    rows.sort(key=lambda r: (r.get("key") or "", r.get("id") or ""))
    return rows


def _load_strategies() -> List[Dict[str, Any]]:
    from core.modules.strategy import Strategy

    rows: List[Dict[str, Any]] = []
    for info in Strategy.list_strategy_infos(enabled_only=False):
        sid = str(
            info.get("unique_relative_path") or info.get("relative_path") or ""
        ).strip()
        rows.append(
            {
                "key": str(info.get("key") or "").strip(),
                "is_enabled": bool(info.get("is_enabled", False)),
                "name": str(info.get("display_name") or "").strip(),
                "id": sid,
            }
        )
    rows.sort(key=lambda r: (r.get("key") or "", r.get("id") or ""))
    return rows


def _load_tag_definitions(tag_ref: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """``tag_ref`` 为 meta.key（推荐）或路径 id。"""
    from core.modules.tag import Tag

    info = Tag().find(tag_ref)
    if info is None:
        return [], f"未找到 tag: {tag_ref}（可用 meta.key，如 market_cap_tier）"
    settings = getattr(info, "settings", None) or {}
    raw = settings.get("tag_definitions") if isinstance(settings, dict) else None
    if not isinstance(raw, list):
        return [], None
    rows: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        rows.append(
            {
                "value": name,
                "name": name,
                "display_name": str(item.get("display_name") or "").strip(),
                "description": str(item.get("description") or "").strip(),
            }
        )
    return rows, None


def _load_indicators() -> List[Dict[str, Any]]:
    from core.modules.indicator import Indicator

    return [{"value": name, "name": name} for name in Indicator.list_indicators()]


def _load_tables() -> List[Dict[str, Any]]:
    from core.modules.data_manager import DataManager

    return [{"value": name, "name": name} for name in DataManager().list_tables()]


def _print_grouped(
    payload: Dict[str, List[Dict[str, Any]]],
    *,
    as_json: bool,
    title: str,
) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
        return
    if not payload:
        print(f"{title}: （无选项）", flush=True)
        return
    for dim, rows in payload.items():
        print(f"[{dim}] {len(rows)} 项", flush=True)
        for row in rows:
            print(f"  {_format_item(row)}", flush=True)
        print(flush=True)


def _print_items(
    resource: str,
    items: Sequence[Dict[str, Any]],
    *,
    as_json: bool,
) -> None:
    if as_json:
        print(
            json.dumps({resource: list(items)}, ensure_ascii=False, indent=2),
            flush=True,
        )
        return
    print(f"[{resource}] {len(items)} 项", flush=True)
    if not items:
        print("  （无）", flush=True)
        return
    for row in items:
        print(f"  {_format_item(row)}", flush=True)


def _format_item(row: Dict[str, Any]) -> str:
    if "key" in row and ("type" in row or "scope" in row):
        key = str(row.get("key") or "")
        ctype = str(row.get("type") or "-")
        scope = str(row.get("scope") or "-")
        name = str(row.get("display_name") or "").strip()
        line = f"{key:<36} type={ctype:<16} scope={scope}"
        if name:
            line = f"{line}  {name}"
        return line

    # tag / strategy：key → is_enabled(bool) → name → id（id 最长放最后）
    if "is_enabled" in row and "id" in row and "key" in row:
        key = str(row.get("key") or "").strip() or "-"
        enabled = bool(row.get("is_enabled"))
        name = str(
            row.get("name") or row.get("display_name") or ""
        ).strip()
        sid = str(row.get("id") or "").strip() or "-"
        parts = [f"{key:<24}", f"is_enabled={enabled}"]
        if name:
            parts.append(name)
        parts.append(f"id={sid}")
        return " ".join(parts)

    value = str(
        row.get("value") or row.get("name") or row.get("key") or ""
    ).strip()
    label = str(
        row.get("label") or row.get("display_name") or ""
    ).strip()
    code = str(row.get("code") or "").strip()
    desc = str(row.get("description") or "").strip()
    parts = [value] if value else []
    if label and label != value:
        parts.append(f"({label})")
    if code and code != value:
        parts.append(f"code={code}")
    if desc:
        parts.append(f"— {desc}")
    return " ".join(parts) if parts else str(row)


__all__ = ["known_resources", "resource_help_lines", "run"]
