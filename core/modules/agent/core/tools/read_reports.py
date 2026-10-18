"""读进度、执行报告、归因报告和扫描摘要。只返回摘要，不回整份 JSON。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.modules.agent.core.tools._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)
from core.modules.agent.core.tools.task_record import task_file
from core.modules.strategy.core.services.progress import PipelineProgress

_LAYER_LABEL = {"enum": "枚举", "price": "价格", "portfolio": "资金"}
_LAYERS = frozenset(_LAYER_LABEL)
_ENUM_FIELDS = (
    "total_opportunities",
    "total_stocks",
    "trigger_stocks",
    "trigger_ratio",
    "avg_per_stock",
    "completed_ratio",
    "unfinished_count",
    "mean_gap",
    "mean_duration",
    "dispersion_conclusion",
    "limit_up_buy_ratio",
    "limit_down_sell_ratio",
)
_PRICE_FIELDS = (
    "win_rate",
    "avg_roi",
    "annual_return",
    "avg_duration_in_days",
    "total_investments",
    "completion_rate",
    "avg_profit_per_investment",
    "stocks_have_opportunities",
    "skipped_buy_at_limit_up",
    "skipped_sell_at_limit_down",
    "skipped_stock_status",
)
_PORTFOLIO_FIELDS = (
    "initial_capital",
    "final_total_equity",
    "total_return",
    "total_trades",
    "win_rate",
    "calmar_ratio",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "max_drawdown_duration_days",
    "average_open_positions",
    "capital_utilization_ratio_pct",
    "top5_profit_concentration_pct",
)


def read_progress(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """读一次后台任务的进度。未完成时不要据此编写结果数字。"""
    if set(arguments) != {"task_id"}:
        return {"ok": False, "error": "只接受参数 task_id"}
    task_id = str(arguments.get("task_id") or "").strip()
    path = task_file(task_id)
    if not path.is_file():
        return {"ok": False, "error": f"找不到任务: {task_id}"}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "error": f"任务记录无法读取: {task_id}"}
    key = str(record.get("key") or "").strip()
    if str(record.get("kind") or "") == "scan":
        return _scan_progress(key, task_id)
    doc = PipelineProgress.get(key, task_id, apply_stale=True)
    if not doc:
        return {"ok": False, "key": key, "task_id": task_id, "error": "进度不存在"}
    status = str(doc.get("status") or "").strip()
    step = doc.get("step") if isinstance(doc.get("step"), dict) else {}
    out: Dict[str, Any] = {
        "ok": True,
        "key": key,
        "task_id": task_id,
        "kind": record.get("kind"),
        "status": status,
        "progress": doc.get("progress"),
        "step": str(step.get("description") or step.get("name") or ""),
    }
    if doc.get("error"):
        out["error"] = str(doc.get("error"))
    if status == "completed" and isinstance(doc.get("result"), dict):
        out["result"] = doc.get("result")
    if status not in {"completed", "failed", "cancelled"}:
        out["note"] = "尚未结束。不要编写结果数字"
    return out


def _scan_progress(key: str, task_id: str) -> Dict[str, Any]:
    from core.modules.strategy.core.services.progress import ScanProgress

    doc = ScanProgress.get_poll_dto(key, task_id)
    if not doc:
        return {"ok": False, "key": key, "task_id": task_id, "error": "进度不存在"}
    status = str(doc.get("status") or "").strip()
    out: Dict[str, Any] = {
        "ok": True,
        "key": key,
        "task_id": task_id,
        "kind": "scan",
        "status": status,
        "progress": doc.get("progress"),
    }
    if doc.get("reason"):
        out["error"] = str(doc.get("reason"))
    report = doc.get("report") if isinstance(doc.get("report"), dict) else {}
    if status == "completed" and report:
        summary = (
            report.get("summary") if isinstance(report.get("summary"), dict) else {}
        )
        out["result"] = {
            "date": str(report.get("date") or ""),
            "total_opportunities": report.get("total_opportunities"),
            "universe": report.get("total_stocks"),
            "hit_stocks": summary.get("total_stocks"),
            "at_limit_up_count": summary.get("at_limit_up_count"),
        }
        out["note"] = "扫描已结束。接着读 read_scan_report，不要编造股票"
    elif status not in {"completed", "failed", "cancelled"}:
        out["note"] = "尚未结束。不要编写机会名单"
    return out


def read_scan_report(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """读一次扫描摘要和前几条机会。不回整份名单。"""
    parsed = _locate_key(arguments, optional={"date"})
    if isinstance(parsed, dict) and parsed.get("ok") is False:
        return parsed
    key, folder = parsed
    day = str(arguments.get("date") or "").strip()
    root = folder / "results" / "scan"
    if not day:
        day = _latest_scan_date(root)
    if not day.isdigit() or len(day) != 8:
        return {"ok": False, "key": key, "error": "没有可读的扫描报告"}
    summary_path = root / day / "scan_summary.json"
    if not _inside(folder, summary_path) or not summary_path.is_file():
        return {
            "ok": False,
            "key": key,
            "error": f"扫描报告不存在: strategies/{key}/results/scan/{day}",
        }
    payload = _read_json(summary_path)
    if payload is None:
        return {"ok": False, "key": key, "error": "扫描报告无法解析"}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    rows = _scan_rows(root / day / "opportunities.csv")
    return {
        "ok": True,
        "key": key,
        "date": day,
        "total_opportunities": payload.get("total_opportunities"),
        "universe": payload.get("total_stocks"),
        "hit_stocks": summary.get("total_stocks"),
        "at_limit_up_count": summary.get("at_limit_up_count"),
        "opportunities": rows,
        "path": f"strategies/{key}/results/scan/{day}",
        "note": "只列出前几条机会。没有出现的股票不要补充",
    }


def _latest_scan_date(root: Path) -> str:
    if not root.is_dir():
        return ""
    days = [
        path.name
        for path in root.iterdir()
        if path.is_dir()
        and path.name.isdigit()
        and len(path.name) == 8
        and (path / "scan_summary.json").is_file()
    ]
    return max(days) if days else ""


def _scan_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    import csv

    out: List[Dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                stock = _json_cell(row.get("stock"))
                out.append(
                    {
                        "stock_id": str(row.get("stock_id") or stock.get("id") or ""),
                        "stock_name": str(
                            row.get("stock_name") or stock.get("name") or ""
                        ),
                        "trigger_date": str(row.get("trigger_date") or ""),
                        "trigger_price": row.get("trigger_price") or "",
                    }
                )
                if len(out) >= 8:
                    break
    except OSError:
        return []
    return out


def _json_cell(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = str(value or "").strip()
    if not text.startswith("{"):
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_execution_report(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """读枚举、价格或资金层的 overall_report 摘要。"""
    parsed = _locate(arguments, optional={"version_id"})
    if isinstance(parsed, dict) and parsed.get("ok") is False:
        return parsed
    key, layer, folder = parsed
    version_id = str(arguments.get("version_id") or "").strip().lstrip("v")
    sim_root = folder / "results" / "simulations"
    if not version_id:
        version_id = _latest_main_version(sim_root, layer)
    if not version_id or not _safe_version(version_id):
        return {
            "ok": False,
            "key": key,
            "error": f"没有可读的{_LAYER_LABEL[layer]}执行报告",
        }
    report_path = sim_root / version_id / layer / "overall_report.json"
    if not _inside(folder, report_path) or not report_path.is_file():
        return {
            "ok": False,
            "key": key,
            "error": f"执行报告不存在: strategies/{key}/results/simulations/{version_id}/{layer}",
        }
    payload = _read_json(report_path)
    if payload is None:
        return {"ok": False, "key": key, "error": "执行报告无法解析"}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    period = (
        payload.get("backtest_period")
        if isinstance(payload.get("backtest_period"), dict)
        else {}
    )
    return {
        "ok": True,
        "key": key,
        "layer": layer,
        "version_id": version_id,
        "period": {
            "start_date": period.get("start_date") or "",
            "end_date": period.get("end_date") or "",
        },
        "summary": _pick(summary, _fields_for(layer)),
        "path": f"strategies/{key}/results/simulations/{version_id}/{layer}/overall_report.json",
        "note": "这是摘要。解释给用户时只用这些数字，不要补充报告里没有的指标",
    }


def read_attribution_report(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """读一层归因的 report.json 摘要：结论、事实和敏感度前几名。"""
    parsed = _locate(arguments, optional={"group_id"})
    if isinstance(parsed, dict) and parsed.get("ok") is False:
        return parsed
    key, layer, folder = parsed
    group_id = str(arguments.get("group_id") or "").strip()
    attr_root = folder / "results" / "attribution"
    if not group_id:
        group_id = _latest_group(attr_root, layer)
    if not group_id.isdigit():
        return {
            "ok": False,
            "key": key,
            "error": f"没有可读的{_LAYER_LABEL[layer]}归因报告",
        }
    report_path = attr_root / group_id / layer / "report.json"
    if not _inside(folder, report_path) or not report_path.is_file():
        return {
            "ok": False,
            "key": key,
            "error": f"归因报告不存在: strategies/{key}/results/attribution/{group_id}/{layer}",
        }
    payload = _read_json(report_path)
    if payload is None:
        return {"ok": False, "key": key, "error": "归因报告无法解析"}
    return {
        "ok": True,
        "key": key,
        "layer": layer,
        "group_id": group_id,
        "baseline_version_id": str(payload.get("baseline_version_id") or ""),
        "analysis_mode": str(payload.get("analysis_mode") or ""),
        "scope_note": str(payload.get("scope_note") or ""),
        "headline": str(payload.get("headline") or ""),
        "sections": _sections(payload.get("sections")),
        "sensitivity_rank": _ranks(payload.get("sensitivity_rank")),
        "path": f"strategies/{key}/results/attribution/{group_id}/{layer}/report.json",
        "note": "改进策略时先看 conclusion 和 sensitivity_rank，不要一次改多个参数",
    }


def _locate_key(arguments: Dict[str, Any], *, optional: set[str]):
    allowed = {"key"} | optional
    if not isinstance(arguments, dict) or not set(arguments) <= allowed:
        names = "、".join(sorted(allowed))
        return {"ok": False, "error": f"只接受参数 {names}"}
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    parsed = parse_strategy_key({"key": arguments.get("key")}, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, _relative = located
    if not folder.is_dir():
        return {"ok": False, "error": f"策略不存在: strategies/{parsed}"}
    return parsed, folder


def _locate(arguments: Dict[str, Any], *, optional: set[str]):
    allowed = {"key", "layer"} | optional
    if not isinstance(arguments, dict) or not set(arguments) <= allowed:
        names = "、".join(sorted(allowed))
        return {"ok": False, "error": f"只接受参数 {names}"}
    if "key" not in arguments or "layer" not in arguments:
        return {"ok": False, "error": "必须提供 key 和 layer"}
    layer = str(arguments.get("layer") or "").strip()
    if layer not in _LAYERS:
        return {"ok": False, "error": "layer 只能是 enum、price 或 portfolio"}
    parsed = parse_strategy_key({"key": arguments.get("key")}, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, _relative = located
    if not folder.is_dir():
        return {"ok": False, "error": f"策略不存在: strategies/{parsed}"}
    return parsed, layer, folder


def _fields_for(layer: str) -> tuple[str, ...]:
    if layer == "enum":
        return _ENUM_FIELDS
    if layer == "price":
        return _PRICE_FIELDS
    return _PORTFOLIO_FIELDS


def _pick(summary: Dict[str, Any], fields: tuple[str, ...]) -> Dict[str, Any]:
    curves = summary.get("curves") if isinstance(summary.get("curves"), dict) else {}
    out: Dict[str, Any] = {}
    for name in fields:
        value = summary.get(name, curves.get(name))
        if value is None or value == "":
            continue
        out[name] = _round(value)
    return out


def _sections(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    out: List[Dict[str, Any]] = []
    for name, block in raw.items():
        if not isinstance(block, dict):
            continue
        facts = [str(item) for item in (block.get("facts") or []) if str(item).strip()]
        out.append(
            {
                "name": str(name),
                "question": str(block.get("question") or ""),
                "conclusion": str(block.get("conclusion") or ""),
                "facts": facts[:6],
            }
        )
        if len(out) >= 8:
            break
    return out


def _ranks(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "rank": item.get("rank"),
                "knob": str(item.get("knob_label") or item.get("knob") or ""),
                "best_value": str(
                    item.get("best_value_label") or item.get("best_value") or ""
                ),
                "span": str(item.get("span_label") or ""),
                "impact": str(item.get("impact") or ""),
            }
        )
        if len(out) >= 5:
            break
    return out


def _latest_main_version(sim_root: Path, layer: str) -> str:
    best = 0
    if not sim_root.is_dir():
        return ""
    for child in sim_root.iterdir():
        if not child.name.isdigit():
            continue
        if (child / layer / "overall_report.json").is_file():
            best = max(best, int(child.name))
    return str(best) if best else ""


def _latest_group(attr_root: Path, layer: str) -> str:
    best = 0
    if not attr_root.is_dir():
        return ""
    for child in attr_root.iterdir():
        if child.name.isdigit() and (child / layer / "report.json").is_file():
            best = max(best, int(child.name))
    return str(best) if best else ""


def _safe_version(version_id: str) -> bool:
    text = str(version_id or "").strip()
    if not text or "/" in text or "\\" in text or ".." in text:
        return False
    head, sep, tail = text.partition("-")
    if not head.isdigit():
        return False
    if not sep:
        return True
    for prefix in ("attr", "roll"):
        if tail.startswith(prefix):
            number = tail[len(prefix) :]
            return number.isdigit() and int(number) > 0
    return False


def _inside(folder: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
    except (OSError, ValueError):
        return False
    return True


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _round(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    return value
