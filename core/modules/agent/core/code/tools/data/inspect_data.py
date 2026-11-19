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


def list_indicators(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """列出可用技术指标名（settings.data.base.indicators）。"""
    _ = arguments
    try:
        from core.modules.indicator import Indicator

        names = list(Indicator.list_indicators())
    except Exception as exc:
        return {"ok": False, "error": f"无法列出指标: {exc}"}
    return {
        "ok": True,
        "indicators": [{"value": n, "name": n} for n in names],
        "count": len(names),
    }


def list_stock_pool_dimensions(
    arguments: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """列出 stock_list_filter 可用维度与选项。可选 dim=area|industry|board|market|list_status。"""
    args = arguments if isinstance(arguments, dict) else {}
    dim = args.get("dim")
    if dim is not None and not isinstance(dim, str):
        return {"ok": False, "error": "dim 须为字符串"}
    extra = set(args) - {"dim"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    dim_norm = str(dim or "").strip() or None
    allowed = {"area", "industry", "board", "market", "list_status"}
    if dim_norm is not None and dim_norm not in allowed:
        return {
            "ok": False,
            "error": f"dim 无效: {dim_norm}，允许 {sorted(allowed)}",
        }
    try:
        options = DataManager().stock.list.load_filter_options(dim_norm)
    except Exception as exc:
        return {"ok": False, "error": f"无法列出股票池维度: {exc}"}
    if not isinstance(options, dict):
        return {"ok": False, "error": "股票池维度返回格式异常"}
    return {
        "ok": True,
        "dim": dim_norm or "all",
        "options": options,
        "note": "value 可直接写入 settings.data.stock_list_filter。",
    }
