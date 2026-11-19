"""只读探查：薄封装 DataManager / DataSource / ContractIssuer。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_contract import ContractIssuer
from core.modules.data_manager import DataManager
from core.modules.data_source import DataSourceManager


def list_data_tables(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    args = arguments if isinstance(arguments, dict) else {}
    owner = str(args.get("owner") or "all").strip().lower() or "all"
    extra = set(args) - {"owner"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    return DataManager().list_tables_by_owner(owner=owner)


def describe_data_table(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"table_name"}:
        return {"ok": False, "error": "只接受参数 table_name"}
    name = arguments.get("table_name")
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "error": "table_name 不能为空"}
    return DataManager().describe_table(table_name=name.strip())


def list_data_contract_keys(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    _ = arguments
    try:
        issuer = ContractIssuer()
        issuer.discover()
        keys = sorted(str(k) for k in issuer.list_available_keys())
    except Exception as exc:
        return {"ok": False, "error": f"无法列出契约: {exc}"}
    return {"ok": True, "keys": keys, "count": len(keys)}


def list_data_sources(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    _ = arguments
    try:
        rows = DataSourceManager().list_renew_targets()
    except Exception as exc:
        return {"ok": False, "error": f"无法列出数据源: {exc}"}
    return {"ok": True, "sources": rows, "count": len(rows)}


def check_data_freshness(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    _ = arguments
    try:
        meta = DataSourceManager.get_data_end_meta_light()
    except Exception:
        try:
            meta = DataSourceManager.get_data_end_meta()
        except Exception as exc:
            return {"ok": False, "error": f"无法读取新鲜度: {exc}"}
    if not isinstance(meta, dict):
        meta = {"raw": meta}
    return {"ok": True, "freshness": meta}
