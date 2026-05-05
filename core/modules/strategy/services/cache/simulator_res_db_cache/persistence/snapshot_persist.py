#!/usr/bin/env python3
"""
DbCache 实现层：``sys_strategy_workbench_snapshot`` 表的加载与持久化（枚举 / 通用 simulator patch）。

命名约定：
- 表中 ``version`` 列 = **snapshot_id**（整型，与领域「快照主键」一一对应）
- 运行状态 JSON 里用 ``workbench_snapshot_version`` 存该整型（与 BFF 一致；曾用名 ``workbench_snapshot_no`` 读时仍兼容）
- 请求主指纹（settings core）↔ **settings_fingerprint_id**，写入列 ``settings_finger_print_id``
- 环境 / scope 指纹 ↔ **env_fingerprint_id**，写入列 ``env_fingerprint_id**
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.infra.project_context.path_manager import PathManager
from ..enumerator.enum_snapshot_payload import (
    cached_storable_to_summary_row,
    load_enum_report_enrichment,
    sanitize_enum_payload_for_snapshot,
    summary_row_to_storable_enum_payload,
)
from ..config import MAX_SNAPSHOT_ROW_UPDATES
from ..audit.result_summary_audit import (
    merge_for_update,
    with_initial_write_count,
)
from ..settings import StrategySettingsService
from core.tables.ui_bff.strategy_workbench_snapshot.model import SysStrategyWorkbenchSnapshotModel

logger = logging.getLogger(__name__)

_SNAPSHOT_CACHE_MAX_AGE = timedelta(hours=24)
_SNAPSHOT_CACHE_MAX_SNAPSHOT_DRIFT = 10


def _row_snapshot_id(row: dict) -> int:
    return int((row or {}).get("snapshot_id") or (row or {}).get("version") or 0)


def _status_bound_snapshot_id(status_payload: Dict[str, Any]) -> int:
    """运行状态里绑定的快照行 id（优先 workbench_snapshot_version）。"""
    return int(
        status_payload.get("workbench_snapshot_version")
        or status_payload.get("workbench_snapshot_no")
        or 0
    )


def _parse_iso_datetime(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _list_snapshot_rows_for_fingerprints(
    strategy_name: str,
    settings_finger_print_id: str,
    env_fingerprint_id: str,
    *,
    limit: int,
) -> List[dict]:
    """按 ``settings_finger_print_id`` + ``env_fingerprint_id`` AND 命中快照行（顺序由 Model 定义）。"""
    model = SysStrategyWorkbenchSnapshotModel()
    return model.list_by_strategy_fingerprints(
        strategy_name,
        settings_finger_print_id=str(settings_finger_print_id or "").strip(),
        env_fingerprint_id=str(env_fingerprint_id or "").strip(),
        limit=limit,
    )


def _materialize_enum_summary_from_snapshot_row(
    strategy_name: str,
    row: Dict[str, Any],
) -> Optional[Tuple[List[Dict[str, Any]], int]]:
    """
    从一行快照的 ``result_summary.enum`` 产出枚举侧 ``summary_row`` 列表与 ``snapshot_id``；
    缺 ``enum`` 载荷或形态不对则 ``None``（由调用方继续扫下一行）。
    """
    rs = row.get("result_summary")
    if not isinstance(rs, dict):
        return None
    enum_snap = rs.get("enum")
    if not isinstance(enum_snap, dict) or not enum_snap:
        return None
    payload = dict(enum_snap)
    enrich = load_enum_report_enrichment(strategy_name, payload)
    if enrich:
        payload.update(enrich)
    summary_row = cached_storable_to_summary_row(strategy_name, payload)
    snapshot_id = _row_snapshot_id(row or {})
    return ([summary_row], snapshot_id)


def _db_cache_row_is_fresh(strategy_name: str, cached_row: dict) -> bool:
    updated = _parse_iso_datetime((cached_row or {}).get("updated_at"))
    if updated is None:
        return False
    now = datetime.now(updated.tzinfo) if updated.tzinfo else datetime.now()
    if now - updated > _SNAPSHOT_CACHE_MAX_AGE:
        return False
    model = SysStrategyWorkbenchSnapshotModel()
    latest_rows = model.list_by_strategy(strategy_name, limit=1)
    if not latest_rows:
        return True
    latest_sid = _row_snapshot_id(latest_rows[0] or {})
    cached_sid = _row_snapshot_id(cached_row or {})
    if latest_sid - cached_sid > _SNAPSHOT_CACHE_MAX_SNAPSHOT_DRIFT:
        return False
    return True


def _workbench_status_path(strategy_name: str):
    return PathManager.userspace() / ".ntq" / "tmp" / "strategy-workbench" / f"{strategy_name}.json"


def _read_workbench_status(strategy_name: str) -> Optional[Dict[str, Any]]:
    path = _workbench_status_path(strategy_name)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "_revision" not in payload:
            payload["_revision"] = 0
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _write_workbench_status(strategy_name: str, payload: Dict[str, Any]) -> None:
    from core.ui.bff.shared.file_ops import atomic_write_text

    path = _workbench_status_path(strategy_name)
    current = _read_workbench_status(strategy_name) or {}
    current_revision = int(current.get("_revision") or 0)
    expected_revision = int(payload.get("_revision") or current_revision)
    if expected_revision != current_revision:
        merged = dict(current)
        merged.update(payload or {})
        payload = merged
    payload["_revision"] = current_revision + 1
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    atomic_write_text(path, content)


def try_load_cached_summary(
    strategy_name: str,
    settings_fingerprint_id: str,
    env_fingerprint_id: str,
) -> Optional[Tuple[List[Dict[str, Any]], int]]:
    """
    编排：**双指纹查表** → **逐行新鲜度** → **取首条可用 ``result_summary.enum`` 并物化为枚举摘要行**。

    返回 ``([summary_row], snapshot_id)``；未命中或枚举载荷不可用则 ``None``。
    （对外仍用此名以保持 ``cache`` 包与枚举入口的惰性导入稳定；展开步骤见
    ``_list_snapshot_rows_for_fingerprints`` / ``_materialize_enum_summary_from_snapshot_row``。）
    """
    sfp = str(settings_fingerprint_id or "").strip()
    efp = str(env_fingerprint_id or "").strip()
    if not sfp:
        return None
    rows = _list_snapshot_rows_for_fingerprints(
        strategy_name,
        sfp,
        efp,
        limit=20,
    )
    for row in rows or []:
        if not _db_cache_row_is_fresh(strategy_name, row):
            continue
        hit = _materialize_enum_summary_from_snapshot_row(strategy_name, row)
        if hit is not None:
            return hit
    return None


def _coerce_settings_snapshot(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw if raw else None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(parsed, dict) and parsed:
            return parsed
    return None


def _enum_meta_now(settings_fp: str, env_fp: str) -> Dict[str, Any]:
    return {
        "settings_finger_print_id": settings_fp,
        "env_fingerprint_id": env_fp,
        "updated_at": datetime.now().astimezone().isoformat(),
    }


def _update_result_summary_audited(
    model: SysStrategyWorkbenchSnapshotModel,
    strategy_name: str,
    snapshot_id: int,
    incoming_rs: Dict[str, Any],
    settings_finger_print_id: str,
    env_fingerprint_id: str,
) -> int:
    """
    合并写入 ``result_summary`` 并递增 ``_db_cache_meta.write_count``。
    若超过 ``MAX_SNAPSHOT_ROW_UPDATES`` 则删除该行，返回 ``-1``。
    """
    current = model.load_by_strategy_snapshot_id(strategy_name, snapshot_id)
    if not current:
        return 0
    prev_rs = current.get("result_summary")
    if not isinstance(prev_rs, dict):
        prev_rs = {}
    merged, outcome = merge_for_update(
        prev_rs,
        incoming_rs,
        max_writes=MAX_SNAPSHOT_ROW_UPDATES,
    )
    if outcome == "delete":
        model.delete_snapshot_row(strategy_name, int(snapshot_id))
        logger.info(
            "快照行因复写次数>%s已删除 | strategy=%s snapshot_id=%s",
            MAX_SNAPSHOT_ROW_UPDATES,
            strategy_name,
            snapshot_id,
        )
        return -1
    return model.update_result_summary(
        strategy_name,
        snapshot_id,
        merged,
        settings_finger_print_id=settings_finger_print_id,
        env_fingerprint_id=env_fingerprint_id,
    )


def _create_snapshot_audited(
    model: SysStrategyWorkbenchSnapshotModel,
    *,
    strategy_name: str,
    settings_snapshot: Dict[str, Any],
    result_summary: Dict[str, Any],
    settings_finger_print_id: str,
    env_fingerprint_id: str,
) -> Dict[str, Any]:
    """新建快照行时为 ``result_summary`` 写入初始 ``write_count``。"""
    rs = with_initial_write_count(dict(result_summary or {}))
    return model.create_snapshot(
        strategy_name=strategy_name,
        settings_snapshot=settings_snapshot or {},
        result_summary=rs,
        settings_finger_print_id=settings_finger_print_id,
        env_fingerprint_id=env_fingerprint_id,
    )


def replace_enum_cache_by_fingerprints(
    *,
    strategy_name: str,
    settings_finger_print_id: str,
    env_fingerprint_id: str,
) -> int:
    """清除匹配指纹行的枚举摘要字段（带写次数审计）。"""
    model = SysStrategyWorkbenchSnapshotModel()
    rows = model.list_by_strategy_fingerprints(
        strategy_name,
        settings_finger_print_id=settings_finger_print_id,
        env_fingerprint_id=env_fingerprint_id,
        limit=500,
    )
    cleared = 0
    for row in rows:
        sid = int((row or {}).get("version") or 0)
        if sid <= 0:
            continue
        rs0 = (row or {}).get("result_summary")
        rs = dict(rs0) if isinstance(rs0, dict) else {}
        rs.pop("enum", None)
        rs.pop("enum_meta", None)
        rc = _update_result_summary_audited(
            model,
            strategy_name,
            sid,
            rs,
            "",
            "",
        )
        if rc != 0:
            cleared += 1
    return cleared


def strip_result_summary_keys_by_fingerprints(
    *,
    strategy_name: str,
    settings_finger_print_id: str,
    env_fingerprint_id: str,
    keys: Sequence[str],
) -> int:
    """按指纹命中行，从 ``result_summary`` 去掉给定顶层键（写次数审计；保留指纹列）。"""
    model = SysStrategyWorkbenchSnapshotModel()
    rows = model.list_by_strategy_fingerprints(
        strategy_name,
        settings_finger_print_id=settings_finger_print_id,
        env_fingerprint_id=env_fingerprint_id,
        limit=500,
    )
    affected = 0
    drop = {str(k) for k in keys if str(k).strip()}
    if not drop:
        return 0
    for row in rows:
        sid = int((row or {}).get("version") or 0)
        if sid <= 0:
            continue
        rs0 = (row or {}).get("result_summary")
        rs = dict(rs0) if isinstance(rs0, dict) else {}
        for k in drop:
            rs.pop(k, None)
        rc = _update_result_summary_audited(
            model,
            strategy_name,
            sid,
            rs,
            str(settings_finger_print_id or ""),
            str(env_fingerprint_id or ""),
        )
        if rc != 0:
            affected += 1
    return affected


def persist_simulator_summary_patch(
    strategy_name: str,
    *,
    settings_snapshot_api: Dict[str, Any],
    result_key: str,
    patch_value: Any,
    settings_finger_print_id: str,
    env_fingerprint_id: str,
) -> int:
    """
    将 ``patch_value`` 写入 ``result_summary[result_key]``（浅覆盖该键），命中双指纹行则 UPDATE，否则 INSERT。

    与枚举专用路径不同：不做 workbench 运行态 JSON 分支；供价格 / 资金等模拟器经 ``DbCacheService.generate_cache`` 调用。
    """
    sfp = str(settings_finger_print_id or "").strip()
    efp = str(env_fingerprint_id or "").strip()
    if not sfp:
        return 0
    rk = str(result_key or "").strip()
    if not rk or rk.startswith("_"):
        return 0

    canonical_settings = StrategySettingsService.canonicalize_api_settings(dict(settings_snapshot_api or {}))
    model = SysStrategyWorkbenchSnapshotModel()
    rows = model.list_by_strategy_fingerprints(
        strategy_name,
        settings_finger_print_id=sfp,
        env_fingerprint_id=efp,
        limit=1,
    )

    if not rows:
        created = _create_snapshot_audited(
            model,
            strategy_name=strategy_name,
            settings_snapshot=canonical_settings,
            result_summary={rk: patch_value},
            settings_finger_print_id=sfp,
            env_fingerprint_id=efp,
        )
        return int(created.get("snapshot_id") or 0)

    sid = _row_snapshot_id(rows[0] or {})
    if sid <= 0:
        return 0
    current = model.load_by_strategy_snapshot_id(strategy_name, sid)
    if not current:
        return 0
    rs0 = current.get("result_summary")
    incoming: Dict[str, Any] = dict(rs0) if isinstance(rs0, dict) else {}
    incoming[rk] = patch_value
    ur = _update_result_summary_audited(
        model,
        strategy_name,
        sid,
        incoming,
        sfp,
        efp,
    )
    if ur == -1:
        snap_for_new = _coerce_settings_snapshot(current.get("settings_snapshot")) or canonical_settings
        created = _create_snapshot_audited(
            model,
            strategy_name=strategy_name,
            settings_snapshot=StrategySettingsService.canonicalize_api_settings(dict(snap_for_new)),
            result_summary={rk: patch_value},
            settings_finger_print_id=sfp,
            env_fingerprint_id=efp,
        )
        return int(created.get("snapshot_id") or 0)
    return sid if ur != 0 else 0


def persist_enum_snapshot(
    strategy_name: str,
    *,
    settings_snapshot_api: Dict[str, Any],
    enum_summary_first_row: Dict[str, Any],
    settings_fingerprint_id: str,
    env_fingerprint_id: str,
    workbench_run_id: Optional[str] = None,
) -> int:
    """
    Write enum summary + fingerprints into sys_strategy_workbench_snapshot.

    Returns affected snapshot_id (best effort; 0 if nothing written).
    """
    sfp = str(settings_fingerprint_id or "").strip()
    efp = str(env_fingerprint_id or "").strip()
    canonical_settings = StrategySettingsService.canonicalize_api_settings(dict(settings_snapshot_api or {}))
    enum_payload = sanitize_enum_payload_for_snapshot(
        summary_row_to_storable_enum_payload(enum_summary_first_row or {})
    )
    model = SysStrategyWorkbenchSnapshotModel()

    try:
        if workbench_run_id:
            status_payload = _read_workbench_status(strategy_name) or {}
            if str(status_payload.get("run_id") or "") != str(workbench_run_id):
                return _persist_cli_style(
                    model,
                    strategy_name,
                    canonical_settings,
                    enum_payload,
                    sfp,
                    efp,
                )
            bound_snapshot_id = _status_bound_snapshot_id(status_payload)
            if bound_snapshot_id > 0 and not sfp:
                current = model.load_by_strategy_snapshot_id(strategy_name, bound_snapshot_id)
                if not current:
                    return 0
                rs0 = current.get("result_summary")
                rs: Dict[str, Any] = dict(rs0) if isinstance(rs0, dict) else {}
                rs["enum"] = enum_payload
                ur = _update_result_summary_audited(
                    model,
                    strategy_name,
                    bound_snapshot_id,
                    rs,
                    "",
                    "",
                )
                if ur == -1:
                    created = _create_snapshot_audited(
                        model,
                        strategy_name=strategy_name,
                        settings_snapshot=canonical_settings,
                        result_summary={"enum": enum_payload},
                        settings_finger_print_id="",
                        env_fingerprint_id="",
                    )
                    new_sid = int(created.get("snapshot_id") or 0)
                    logger.warning(
                        "枚举快照写入 fallback（无 settings 指纹，复写超限删行后新建） | strategy=%s snapshot_id=%s",
                        strategy_name,
                        new_sid,
                    )
                    return new_sid
                logger.warning(
                    "枚举快照写入 fallback（无 settings 指纹） | strategy=%s snapshot_id=%s",
                    strategy_name,
                    bound_snapshot_id,
                )
                return bound_snapshot_id
            if bound_snapshot_id <= 0 or not sfp:
                run_snap = _coerce_settings_snapshot(status_payload.get("run_settings_snapshot"))
                snap_for_row = run_snap if isinstance(run_snap, dict) and run_snap else canonical_settings
                matched_rows = model.list_by_strategy_fingerprints(
                    strategy_name,
                    settings_finger_print_id=sfp,
                    env_fingerprint_id=efp,
                    limit=1,
                )
                if matched_rows:
                    matched_sid = _row_snapshot_id(matched_rows[0] or {})
                    if matched_sid > 0:
                        rs0 = (matched_rows[0] or {}).get("result_summary")
                        rs_m = dict(rs0) if isinstance(rs0, dict) else {}
                        rs_m["enum"] = enum_payload
                        rs_m["enum_meta"] = _enum_meta_now(sfp, efp)
                        ur = _update_result_summary_audited(
                            model,
                            strategy_name,
                            matched_sid,
                            rs_m,
                            sfp,
                            efp,
                        )
                        if ur == -1:
                            created = _create_snapshot_audited(
                                model,
                                strategy_name=strategy_name,
                                settings_snapshot=StrategySettingsService.canonicalize_api_settings(
                                    dict(snap_for_row)
                                ),
                                result_summary={
                                    "enum": enum_payload,
                                    "enum_meta": _enum_meta_now(sfp, efp),
                                },
                                settings_finger_print_id=sfp,
                                env_fingerprint_id=efp,
                            )
                            new_sid = int(created.get("snapshot_id") or 0)
                            if new_sid > 0:
                                status_payload["workbench_snapshot_version"] = new_sid
                                status_payload.pop("workbench_snapshot_no", None)
                                status_payload["updated_at"] = datetime.now().astimezone().isoformat()
                                _write_workbench_status(strategy_name, status_payload)
                                logger.info(
                                    "枚举快照写入（复写超限删行后新建） | strategy=%s snapshot_id=%s",
                                    strategy_name,
                                    new_sid,
                                )
                            return new_sid
                        status_payload["workbench_snapshot_version"] = matched_sid
                        status_payload.pop("workbench_snapshot_no", None)
                        status_payload["updated_at"] = datetime.now().astimezone().isoformat()
                        _write_workbench_status(strategy_name, status_payload)
                        logger.info(
                            "枚举快照写入（命中同指纹合并） | strategy=%s snapshot_id=%s settings_fp=%s",
                            strategy_name,
                            matched_sid,
                            sfp,
                        )
                        return matched_sid
                created = _create_snapshot_audited(
                    model,
                    strategy_name=strategy_name,
                    settings_snapshot=StrategySettingsService.canonicalize_api_settings(dict(snap_for_row)),
                    result_summary={
                        "enum": enum_payload,
                        "enum_meta": _enum_meta_now(sfp, efp),
                    },
                    settings_finger_print_id=sfp,
                    env_fingerprint_id=efp,
                )
                new_sid = int(created.get("snapshot_id") or 0)
                if new_sid > 0:
                    status_payload["workbench_snapshot_version"] = new_sid
                    status_payload.pop("workbench_snapshot_no", None)
                    status_payload["updated_at"] = datetime.now().astimezone().isoformat()
                    _write_workbench_status(strategy_name, status_payload)
                    logger.info(
                        "枚举快照写入（新建快照行） | strategy=%s snapshot_id=%s settings_fp=%s",
                        strategy_name,
                        new_sid,
                        sfp,
                    )
                return new_sid
            current = model.load_by_strategy_snapshot_id(strategy_name, bound_snapshot_id)
            if not current:
                return 0
            rs0 = current.get("result_summary")
            rs_u: Dict[str, Any] = dict(rs0) if isinstance(rs0, dict) else {}
            rs_u["enum"] = enum_payload
            rs_u["enum_meta"] = _enum_meta_now(sfp, efp)
            ur = _update_result_summary_audited(
                model,
                strategy_name,
                bound_snapshot_id,
                rs_u,
                sfp,
                efp,
            )
            if ur == -1:
                snap_for_new = _coerce_settings_snapshot(current.get("settings_snapshot"))
                if not isinstance(snap_for_new, dict) or not snap_for_new:
                    snap_for_new = canonical_settings
                created = _create_snapshot_audited(
                    model,
                    strategy_name=strategy_name,
                    settings_snapshot=StrategySettingsService.canonicalize_api_settings(dict(snap_for_new)),
                    result_summary={
                        "enum": enum_payload,
                        "enum_meta": _enum_meta_now(sfp, efp),
                    },
                    settings_finger_print_id=sfp,
                    env_fingerprint_id=efp,
                )
                new_sid = int(created.get("snapshot_id") or 0)
                if new_sid > 0:
                    status_payload["workbench_snapshot_version"] = new_sid
                    status_payload.pop("workbench_snapshot_no", None)
                    status_payload["updated_at"] = datetime.now().astimezone().isoformat()
                    _write_workbench_status(strategy_name, status_payload)
                    logger.info(
                        "枚举快照写入（绑定行复写超限删行后新建） | strategy=%s snapshot_id=%s settings_fp=%s",
                        strategy_name,
                        new_sid,
                        sfp,
                    )
                return new_sid
            logger.info(
                "枚举快照写入（更新当前绑定行） | strategy=%s snapshot_id=%s settings_fp=%s",
                strategy_name,
                bound_snapshot_id,
                sfp,
            )
            return bound_snapshot_id

        return _persist_cli_style(model, strategy_name, canonical_settings, enum_payload, sfp, efp)
    except Exception:
        logger.exception("persist_enum_snapshot failed | strategy=%s", strategy_name)
        return 0


def _persist_cli_style(
    model: SysStrategyWorkbenchSnapshotModel,
    strategy_name: str,
    canonical_settings: Dict[str, Any],
    enum_payload: Dict[str, Any],
    sfp: str,
    efp: str,
) -> int:
    if sfp:
        matched_rows = model.list_by_strategy_fingerprints(
            strategy_name,
            settings_finger_print_id=sfp,
            env_fingerprint_id=efp,
            limit=1,
        )
        if matched_rows:
            matched_sid = _row_snapshot_id(matched_rows[0] or {})
            if matched_sid > 0:
                rs0 = (matched_rows[0] or {}).get("result_summary")
                rs_m = dict(rs0) if isinstance(rs0, dict) else {}
                rs_m["enum"] = enum_payload
                rs_m["enum_meta"] = _enum_meta_now(sfp, efp)
                ur = _update_result_summary_audited(
                    model,
                    strategy_name,
                    matched_sid,
                    rs_m,
                    sfp,
                    efp,
                )
                if ur == -1:
                    created = _create_snapshot_audited(
                        model,
                        strategy_name=strategy_name,
                        settings_snapshot=canonical_settings,
                        result_summary={
                            "enum": enum_payload,
                            "enum_meta": _enum_meta_now(sfp, efp),
                        },
                        settings_finger_print_id=sfp,
                        env_fingerprint_id=efp,
                    )
                    new_sid = int(created.get("snapshot_id") or 0)
                    if new_sid > 0:
                        logger.info(
                            "枚举快照写入 CLI（复写超限删行后新建） | strategy=%s snapshot_id=%s",
                            strategy_name,
                            new_sid,
                        )
                    return new_sid
                logger.info(
                    "枚举快照写入 CLI（合并指纹） | strategy=%s snapshot_id=%s",
                    strategy_name,
                    matched_sid,
                )
                return matched_sid
    created = _create_snapshot_audited(
        model,
        strategy_name=strategy_name,
        settings_snapshot=canonical_settings,
        result_summary={
            "enum": enum_payload,
            "enum_meta": _enum_meta_now(sfp, efp),
        },
        settings_finger_print_id=sfp,
        env_fingerprint_id=efp,
    )
    new_sid = int(created.get("snapshot_id") or 0)
    if new_sid > 0:
        logger.info("枚举快照写入 CLI（新建快照行） | strategy=%s snapshot_id=%s", strategy_name, new_sid)
    return new_sid


__all__ = [
    "persist_enum_snapshot",
    "persist_simulator_summary_patch",
    "replace_enum_cache_by_fingerprints",
    "strip_result_summary_keys_by_fingerprints",
    "try_load_cached_summary",
]
