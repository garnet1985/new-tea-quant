"""工作台快照与 HTTP 契约：latest / 按 id、apply（V2-09）、按 step 报告（V2-07）。"""

from __future__ import annotations

import json
import logging
import os
import pprint
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional, Tuple

from core.infra.project_context.path_manager import PathManager
from core.modules.data_manager import DataManager
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper
from core.modules.strategy.services.cache.simulator_res_db_cache.report_slot_disk_hydrate import (
    attach_enum_opportunities_field,
    enum_opportunity_count_from_slot,
    hydrate_capital_slot,
    hydrate_enum_slot,
    hydrate_workbench_result_report,
)

from .run_service import StrategySettingsService

logger = logging.getLogger(__name__)

_MAX_ROW_REPAIR_LOOPS = 5


def _resolve_capital_report_slot(strategy_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """读取当前快照行 ``capital_allocation`` 槽；无槽则空。"""
    rr = dict(row.get("result_report") or {})
    raw = rr.get("capital_allocation")
    if not isinstance(raw, dict) or not raw:
        return {}
    hydrated = hydrate_capital_slot(str(strategy_name).strip(), raw)
    if isinstance(hydrated, dict) and hydrated.get("initial_capital") is not None:
        return hydrated
    return raw


def _resolve_enum_report_slot(strategy_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """读取当前快照行 ``enum`` 槽；无槽则空。"""
    sn = str(strategy_name).strip()
    rr = dict(row.get("result_report") or {})
    raw = rr.get("enum")
    if not isinstance(raw, dict) or not raw:
        return {}
    hydrated = attach_enum_opportunities_field(hydrate_enum_slot(sn, raw))
    return dict(hydrated) if isinstance(hydrated, dict) and hydrated else {}


def _snapshot_model():
    return DataManager().get_table("sys_strategy_workbench_snapshot")


def _load_latest_row(model, strategy_name: str) -> Optional[Dict[str, Any]]:
    if model is None:
        return None
    rows = model.list_by_strategy(str(strategy_name), limit=1)
    if not rows:
        return None
    return dict(rows[0] or {})


def _row_usable(row: Dict[str, Any]) -> bool:
    return isinstance(row.get("settings_snapshot"), dict)


def fetch_workbench_by_version(
    strategy_name: str, version: int
) -> Optional[Dict[str, Any]]:
    """
    按 ``strategy_name`` + 工作台 ``version``（表中列名）读取一行。

    不存在、``version`` 非正、或 ``settings_snapshot`` 不可用 → ``None``（与 **V2-08** 404 对齐）。
    """
    name = str(strategy_name or "").strip()
    sid = int(version)
    if not name or sid <= 0:
        return None

    model = _snapshot_model()
    if model is None:
        logger.error("Workbench snapshot table is not registered")
        return None

    row = model.load_by_strategy_version(name, sid)
    if not row or not _row_usable(row):
        return None
    out = dict(row)
    # 合并差异字段和磁盘上的 settings
    settings_diff = out.get("settings_snapshot")  # 数据库中存储的是差异字段
    if isinstance(settings_diff, dict) and settings_diff:
        from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_diff import (
            merge_settings,
        )
        folder = PathManager.strategy(name)
        discovered = StrategyDiscoveryHelper.load_strategy(folder)
        if discovered is not None:
            disk_settings = dict(discovered.settings.to_dict())
            merged_settings = merge_settings(disk_settings, settings_diff)
            out["settings_snapshot"] = merged_settings  # 替换为合并后的完整 settings
    rr = row.get("result_report") or {}
    if isinstance(rr, dict):
        rr = hydrate_workbench_result_report(name, rr)
        en_slot = rr.get("enum")
        if isinstance(en_slot, dict) and en_slot:
            if enum_opportunity_count_from_slot(en_slot) is not None:
                rr = dict(rr)
                rr["enum"] = attach_enum_opportunities_field(en_slot)
        out["result_report"] = rr
    return out


def _synthetic_cold_start_snapshot_row(
    strategy_name: str, settings_api: Dict[str, Any]
) -> Dict[str, Any]:
    """未落库时的合成行：仅 settings，``version==0``（不落 DB）。"""
    name = str(strategy_name or "").strip()
    return {
        "strategy_name": name,
        "version": 0,
        "settings_snapshot": dict(settings_api or {}),
        "reports": {},
        "result_report": {},
        "settings_finger_print_id": "",
        "env_fingerprint_id": "",
    }


def workbench_latest_ui_flags(strategy_name: str, row: Dict[str, Any]) -> Dict[str, bool]:
    """供 V2-01：是否已有持久化快照、是否存在可对比的其它版本（≥2 条快照）。"""
    sid = int(row.get("version") or 0)
    model = _snapshot_model()
    n = 0
    if model is not None:
        n = len(model.list_by_strategy(str(strategy_name).strip(), limit=500) or [])
    return {
        "has_persisted_snapshot": sid > 0,
        "has_other_versions": sid > 0 and n >= 2,
    }


def fetch_latest_workbench_snapshot(strategy_name: str) -> Optional[Dict[str, Any]]:
    """
    返回该策略快照表最新一行；若无表数据则从 userspace ``settings.py`` discovery 得到 **合成行**
   （不写 DB，直至某步 run 结束经 DbCache 持久化）。

    无法加载策略时返回 ``None``（仅依赖快照表与 discovery，无 BFF / Flask）。
    """
    name = str(strategy_name or "").strip()
    if not name:
        return None

    model = _snapshot_model()
    if model is None:
        logger.error("Workbench snapshot table is not registered")
        return None

    for _ in range(_MAX_ROW_REPAIR_LOOPS):
        row = _load_latest_row(model, name)
        if not row:
            break
        if _row_usable(row):
            out = dict(row)
            # 合并差异字段和磁盘上的 settings
            settings_diff = out.get("settings_snapshot")  # 数据库中存储的是差异字段
            if isinstance(settings_diff, dict) and settings_diff:
                from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_diff import (
                    merge_settings,
                )
                folder = PathManager.strategy(name)
                discovered = StrategyDiscoveryHelper.load_strategy(folder)
                if discovered is not None:
                    disk_settings = dict(discovered.settings.to_dict())
                    merged_settings = merge_settings(disk_settings, settings_diff)
                    out["settings_snapshot"] = merged_settings  # 替换为合并后的完整 settings
            rr = out.get("result_report")
            if isinstance(rr, dict):
                out["result_report"] = hydrate_workbench_result_report(name, rr)
            return out
        sid = int(row.get("version") or 0)
        if sid <= 0:
            logger.warning("Unusable snapshot row for %s (missing version)", name)
            break
        logger.warning("Removing unusable workbench snapshot row strategy=%s version=%s", name, sid)
        from core.modules.strategy.services.data.output.workbench_snapshot_retention import (
            log_workbench_version_deleted,
        )

        log_workbench_version_deleted(name, sid, row)
        model.delete_version_row(name, sid)

    folder = PathManager.strategy(name)
    discovered = StrategyDiscoveryHelper.load_strategy(folder)
    if discovered is None:
        return None

    merged = dict(discovered.settings.to_dict())
    settings_api, err = StrategySettingsService.normalize_runtime_settings(
        strategy_name=name,
        api_settings=merged,
    )
    if err or not settings_api:
        logger.error("Workbench cold start normalize failed for %s: %s", name, err)
        return None

    return _synthetic_cold_start_snapshot_row(name, settings_api)


# --- V2-09：快照 settings → userspace（与 ``core.ui.bff.shared.file_ops`` 同语义，避免依赖 BFF 包初始化链） ---


def _atomic_write_text(target_path: Path, content: str, encoding: str = "utf-8") -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, dir=target_path.parent, delete=False) as tmp:
        tmp.write(content)
        temp_path = Path(tmp.name)
    os.replace(str(temp_path), str(target_path))


def _backup_settings_file(strategy_name: str) -> None:
    settings_file = PathManager.strategy_settings(strategy_name)
    if settings_file.is_file():
        backup_path = settings_file.with_suffix(settings_file.suffix + ".bak")
        backup_path.write_text(settings_file.read_text(encoding="utf-8"), encoding="utf-8")


def _write_settings_py(strategy_name: str, settings: Dict[str, Any], pretty: bool) -> None:
    settings_file = PathManager.strategy_settings(strategy_name)
    if pretty:
        literal = pprint.pformat(dict(settings or {}), width=100, sort_dicts=True)
    else:
        literal = repr(dict(settings or {}))
    content = (
        "# Auto-generated by Strategy Workbench (apply snapshot version to userspace).\n"
        "# Manual edits are allowed; next save from Workbench may reformat this file.\n\n"
        f"settings = {literal}\n"
    )
    _atomic_write_text(settings_file, content)


def apply_workbench_snapshot_settings_to_userspace(
    *,
    strategy_name: str,
    version: int,
    pretty: bool = False,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    读取一行快照 → 规范化 settings → 备份并原子写入 ``settings.py`` → 刷新该行 ``updated_at``。

    成功返回 ``({"applied": True, "strategy_name", "version_id"}, None)``。
    """
    name = str(strategy_name or "").strip()
    sid = int(version)
    if not name or sid <= 0:
        return None, "参数无效"

    row = fetch_workbench_by_version(name, sid)
    if not row:
        return None, "快照不存在"

    settings_snapshot = row.get("settings_snapshot") or {}
    normalized, err = StrategySettingsService.normalize_runtime_settings(
        strategy_name=name,
        api_settings=settings_snapshot,
    )
    if err or not normalized:
        return None, err or "settings 校验失败"

    try:
        _backup_settings_file(name)
        _write_settings_py(name, normalized, pretty)
    except Exception as e:
        logger.exception("apply-settings 写盘失败 strategy=%s version=%s", name, sid)
        return None, f"写盘失败: {e}"

    model = _snapshot_model()
    if model is None:
        logger.error("sys_strategy_workbench_snapshot 未注册，写盘已成功")
        return None, "存储不可用"

    try:
        n = int(model.touch_version_updated_at(name, sid) or 0)
        if n <= 0:
            return None, "更新快照时间失败: 行不存在或无法更新"
    except Exception as e:
        logger.exception("touch_version_updated_at failed")
        return None, f"更新快照时间失败: {e}"

    return (
        {
            "applied": True,
            "strategy_name": name,
            "version_id": f"v{sid}",
        },
        None,
    )


# --- V2-07：按 step 读 ``result_report`` 槽位 ---

_STEP_TO_REPORT_SLOT = {
    "enum": "enum",
    "price": "price_factor",
    "capital": "capital_allocation",
}


def parse_version_id(version_id: str) -> Optional[int]:
    """接受 ``v3`` / ``3`` 等形式。"""
    s = str(version_id or "").strip()
    if not s:
        return None
    if s.lower().startswith("v"):
        s = s[1:]
    try:
        n = int(s)
        return n if n > 0 else None
    except ValueError:
        return None


def build_step_report_message(
    *,
    strategy_name: str,
    normalized_step: str,
    version: int,
) -> Optional[Dict[str, Any]]:
    """读快照一行该 step 槽位报告；行不存在 ``None``。"""
    slot = _STEP_TO_REPORT_SLOT.get(normalized_step)
    if not slot:
        return None

    model = _snapshot_model()
    if model is None:
        return None

    name = str(strategy_name).strip()
    row = fetch_workbench_by_version(name, int(version))
    if not row:
        return None

    rr = row.get("result_report") or {}
    raw = rr.get(slot)
    if slot == "enum":
        report = _resolve_enum_report_slot(name, row)
    elif slot == "capital_allocation":
        report = _resolve_capital_report_slot(name, row)
    elif raw is None:
        report = {}
    elif isinstance(raw, dict):
        report = raw
    else:
        report = raw

    return {
        "version_id": f"v{int(version)}",
        "strategy_name": name,
        "step": normalized_step,
        "report": report,
    }


_STOCK_REF_FILENAMES = ("0_stock_ref.json",)


def _enum_output_dir_candidates_for_ref(strategy_name: str, row: Dict[str, Any]) -> List[str]:
    version = int(row.get("version") or 0)
    base = PathManager.strategy_simulation_enum(strategy_name)
    candidates_dirs: List[str] = []

    rr = row.get("result_report") or {}
    enum_raw = rr.get("enum")
    if isinstance(enum_raw, dict):
        out_d = str(enum_raw.get("enumerator_output_dir") or "").strip()
        if out_d:
            candidates_dirs.append(out_d)
        vid = enum_raw.get("output_version_id")
        if vid is not None:
            try:
                vs = str(int(vid))
                if vs not in candidates_dirs:
                    candidates_dirs.append(vs)
            except (TypeError, ValueError):
                pass

    if version > 0:
        sid_s = str(int(version))
        if sid_s not in candidates_dirs:
            candidates_dirs.append(sid_s)

    seen: set[str] = set()
    uniq: List[str] = []
    for d in candidates_dirs:
        if d and d not in seen:
            seen.add(d)
            uniq.append(d)
    return [str(base / d) for d in uniq]


def _price_output_dir_candidates_for_ref(strategy_name: str, row: Dict[str, Any]) -> List[str]:
    base = PathManager.strategy_simulation_price(strategy_name)
    candidates_dirs: List[str] = []

    rr = row.get("result_report") or {}
    price_raw = rr.get("price_factor")
    if isinstance(price_raw, dict):
        run = price_raw.get("output_version_run")
        if isinstance(run, dict):
            out_d = str(run.get("output_version_dir") or "").strip()
            if out_d:
                candidates_dirs.append(out_d)
            vid = run.get("output_version_id")
            if vid is not None:
                try:
                    vs = str(int(vid))
                    if vs not in candidates_dirs:
                        candidates_dirs.append(vs)
                except (TypeError, ValueError):
                    pass
        vid_top = price_raw.get("output_version_id")
        if vid_top is not None:
            try:
                vs = str(int(vid_top))
                if vs not in candidates_dirs:
                    candidates_dirs.append(vs)
            except (TypeError, ValueError):
                pass

    seen: set[str] = set()
    uniq: List[str] = []
    for d in candidates_dirs:
        if d and d not in seen:
            seen.add(d)
            uniq.append(d)
    return [str(base / d) for d in uniq]


def build_step_report_ref_message(
    *,
    strategy_name: str,
    normalized_step: str,
    version: int,
) -> Optional[Dict[str, Any]]:
    """
    读取步骤产物目录下的逐股 ref（枚举 ``0_stock_ref.json``；价格回测同文件名或扫描单股 JSON）。

    仅当快照行不存在（或参数非法）时返回 ``None``，路由 404。磁盘已清理、文件不存在时为正常情况，
    仍返回 dict：``stock_ref_available=False``、``stock_ref=null``。
    """
    if normalized_step not in ("enum", "price"):
        return None
    name = str(strategy_name).strip()
    if not name or version <= 0:
        return None

    row = fetch_workbench_by_version(name, int(version))
    if not row:
        return None

    stock_ref: Optional[Dict[str, Any]] = None
    resolved_dir = ""

    if normalized_step == "enum":
        for dir_path in _enum_output_dir_candidates_for_ref(name, row):
            p = Path(dir_path)
            for fname in _STOCK_REF_FILENAMES:
                ref_path = p / fname
                if not ref_path.is_file():
                    continue
                try:
                    raw = json.loads(ref_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(raw, dict) and raw:
                    # 过滤掉没有对应机会数据文件的股票
                    valid_stocks: Dict[str, Any] = {}
                    for sid in raw:
                        opportunity_file = p / f"{sid}_opportunities.csv"
                        if opportunity_file.is_file():
                            # 检查文件内容是否非空（至少有表头和一行数据）
                            try:
                                content = opportunity_file.read_text(encoding="utf-8")
                                lines = [line.strip() for line in content.split("\n") if line.strip()]
                                if len(lines) >= 2:
                                    valid_stocks[sid] = raw[sid]
                            except Exception:
                                continue
                    stock_ref = valid_stocks
                    resolved_dir = p.name
                    break
            if stock_ref is not None:
                break
    else:
        from core.modules.strategy.engines.simulator.price_factor.stock_ref import (
            load_price_stock_ref_from_dir,
        )

        for dir_path in _price_output_dir_candidates_for_ref(name, row):
            p = Path(dir_path)
            if not p.is_dir():
                continue
            loaded = load_price_stock_ref_from_dir(p)
            if loaded:
                stock_ref = loaded
                resolved_dir = p.name
                break

    common = {
        "version_id": f"v{int(version)}",
        "strategy_name": name,
        "step": normalized_step,
    }
    if stock_ref is None:
        return {
            **common,
            "stock_ref": None,
            "stock_ref_available": False,
            "resolved_output_dir": "",
        }

    stock_ref = _enrich_stock_ref_with_list_names(stock_ref)

    return {
        **common,
        "stock_ref": stock_ref,
        "stock_ref_available": True,
        "resolved_output_dir": resolved_dir,
    }


def _batch_load_stock_display_names(codes: List[str]) -> Dict[str, str]:
    """``sys_stock_list.id`` (ts_code) → ``name``，批量查询。"""
    model = DataManager().get_table("sys_stock_list")
    if model is None or not codes:
        return {}
    out: Dict[str, str] = {}
    deduped = list(dict.fromkeys(c for c in codes if c))
    chunk_size = 500
    for i in range(0, len(deduped), chunk_size):
        chunk = deduped[i : i + chunk_size]
        ph = ",".join(["%s"] * len(chunk))
        try:
            rows = model.load(f"id IN ({ph})", tuple(chunk))
        except Exception:
            continue
        for r in rows or []:
            rec = dict(r or {})
            sid = str(rec.get("id") or "").strip()
            nm = str(rec.get("name") or "").strip()
            if sid and nm:
                out[sid] = nm
    return out


def _enrich_stock_ref_with_list_names(stock_ref: Dict[str, Any]) -> Dict[str, Any]:
    """``stock_name`` 与 ts_code 相同或为空时，用 ``sys_stock_list.name`` 覆盖（证券简称）。"""
    if not isinstance(stock_ref, dict) or not stock_ref:
        return stock_ref
    need: List[str] = []
    for sid, payload in stock_ref.items():
        code = str(sid).strip()
        if not code:
            continue
        row = payload if isinstance(payload, dict) else {}
        sn = str(row.get("stock_name") or "").strip()
        if not sn or sn == code:
            need.append(code)
    names = _batch_load_stock_display_names(need)
    if not names:
        return stock_ref
    out: Dict[str, Any] = {}
    for sid, payload in stock_ref.items():
        code = str(sid).strip()
        base = dict(payload) if isinstance(payload, dict) else {}
        sn = str(base.get("stock_name") or "").strip()
        if (not sn or sn == code) and code in names:
            base["stock_name"] = names[code]
        out[str(sid)] = base
    return out


def clear_workbench_simulation_cache_all() -> Dict[str, Any]:
    """
    清空 ``sys_strategy_workbench_snapshot`` 全表（模拟结果 DbCache）。

    仅删 DB 行；磁盘 ``results/simulations/`` 目录不在此接口范围内。
    """
    from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
        SimulatorResDbCacheService,
    )

    svc = SimulatorResDbCacheService()
    if svc.table_operator is None:
        return {"ok": False, "error": "存储不可用", "deleted_count": 0}
    deleted = int(svc.delete_all_cache() or 0)
    return {"ok": True, "deleted_count": deleted, "cleared": deleted >= 0}


def clear_workbench_simulation_cache_by_version(
    strategy_name: str, version: int
) -> Dict[str, Any]:
    """删除指定 ``strategy_name`` + 工作台 ``version`` 的一条快照行。"""
    from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
        SimulatorResDbCacheService,
    )

    name = str(strategy_name or "").strip()
    sid = int(version)
    if not name or sid <= 0:
        return {"ok": False, "error": "参数无效", "deleted": False}
    svc = SimulatorResDbCacheService()
    if svc.table_operator is None:
        return {"ok": False, "error": "存储不可用", "deleted": False}
    deleted = bool(svc.delete_cache_by_version(name, sid))
    if not deleted:
        return {
            "ok": False,
            "error": "快照不存在",
            "deleted": False,
            "strategy_name": name,
            "version": sid,
        }
    return {
        "ok": True,
        "deleted": True,
        "strategy_name": name,
        "version": sid,
        "version_id": f"v{sid}",
    }
