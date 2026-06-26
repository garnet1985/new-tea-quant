#!/usr/bin/env python3
"""
磁盘 ``output_version`` 目录保留策略（enum / price / capital）。

与 ``WorkbenchSnapshotRetention``（DB 工作台 ``version`` 行）分离：
本模块只 ``rmtree`` ``results/simulations/{enum|price|capital}/<id>/``，不删 DB 行。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Set

from core.infra.project_context import ProjectContext
from core.modules.data_manager import DataManager

from .version_manager import StrategyOutputVersionService

logger = logging.getLogger(__name__)

_SimKind = Literal["enum", "price", "capital"]


def _simulation_root(sim_kind: _SimKind):
    """运行时解析路径函数"""
    if sim_kind == "enum":
        return ProjectContext.get_strategy_directory_simulation_enum
    if sim_kind == "price":
        return ProjectContext.get_strategy_directory_simulation_price
    return ProjectContext.get_strategy_directory_simulation_capital


def resolve_max_output_versions(settings: Dict[str, Any]) -> int:
    """磁盘保留上限：``simulation.retention.max_output_versions``（默认 3）。"""
    if not isinstance(settings, dict):
        return 3
    simulation = settings.get("simulation")
    if isinstance(simulation, dict):
        retention = simulation.get("retention")
        if isinstance(retention, dict) and retention.get("max_output_versions") is not None:
            try:
                return max(int(retention["max_output_versions"]), 1)
            except (TypeError, ValueError):
                pass
    return 3


def _normalize_protect_output_version_dir(value: Any) -> str:
    """``protect_output_version_dir`` 接受目录名或 ``Path``（及绝对路径字符串）。"""
    if value is None:
        return ""
    if isinstance(value, Path):
        return str(value.name).strip()
    s = str(value).strip()
    if not s:
        return ""
    if "/" in s or "\\" in s:
        return Path(s).name
    return s


def _norm_dir_name(value: Any) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    if "/" in s:
        s = s.rsplit("/", 1)[-1].strip()
    return s


def _add_dir_name(target: Set[str], value: Any) -> None:
    name = _norm_dir_name(value)
    if name and name[0].isdigit():
        target.add(name)


def _protected_dirs_from_result_report(
    rr: Dict[str, Any], *, strategy_name: str = ""
) -> Dict[_SimKind, Set[str]]:
    out: Dict[_SimKind, Set[str]] = {"enum": set(), "price": set(), "capital": set()}
    if not isinstance(rr, dict):
        return out

    enum_raw = rr.get("enum")
    if isinstance(enum_raw, dict):
        _add_dir_name(out["enum"], enum_raw.get("enumerator_output_dir"))

    pf = rr.get("price_factor")
    if isinstance(pf, dict):
        run = pf.get("output_version_run")
        if isinstance(run, dict):
            _add_dir_name(out["price"], run.get("output_version_dir"))
        ov = pf.get("output_version")
        if isinstance(ov, dict):
            _add_dir_name(out["enum"], ov.get("enumerator_output_dir"))
            sn = str(strategy_name or "").strip()
            edir = str(ov.get("enumerator_output_dir") or "").strip()
            if sn and edir:
                from core.modules.strategy.services.cache.simulator_res_db_cache.report_slot_disk_hydrate import (
                    resolve_capital_output_dir_for_enum_run,
                )

                _add_dir_name(
                    out["capital"],
                    resolve_capital_output_dir_for_enum_run(sn, edir),
                )

    cap = rr.get("capital_allocation")
    if isinstance(cap, dict):
        _add_dir_name(out["capital"], cap.get("capital_output_version_dir"))
        ov = cap.get("output_version")
        if isinstance(ov, dict):
            _add_dir_name(out["enum"], ov.get("enumerator_output_dir"))

    return out


def collect_referenced_output_version_dirs(strategy_name: str) -> Dict[_SimKind, Set[str]]:
    """汇总 DB 快照 ``result_report`` 与磁盘 metadata 中仍被引用的目录名（数字 id）。"""
    sn = str(strategy_name or "").strip()
    merged: Dict[_SimKind, Set[str]] = {"enum": set(), "price": set(), "capital": set()}
    if not sn:
        return merged

    model = DataManager().get_table("sys_strategy_workbench_snapshot")
    if model is not None:
        try:
            rows = model.list_by_strategy(sn, limit=500) or []
        except Exception:
            rows = []
        for row in rows:
            refs = _protected_dirs_from_result_report(
                dict((row or {}).get("result_report") or {}),
                strategy_name=sn,
            )
            for kind in ("enum", "price", "capital"):
                merged[kind].update(refs[kind])

    _scan_disk_metadata_refs(sn, merged)
    return merged


def _scan_disk_metadata_refs(strategy_name: str, merged: Dict[_SimKind, Set[str]]) -> None:
    """从 price/capital 的 ``0_metadata.json`` / session 摘要补全对 enum 目录的引用。"""
    for kind in ("enum", "price", "capital"):
        root = _simulation_root(kind)(strategy_name)
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir() or not child.name.isdigit():
                continue
            meta_path = child / "0_metadata.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
                if isinstance(meta, dict):
                    ov = meta.get("output_version")
                    if isinstance(ov, dict):
                        _add_dir_name(merged["enum"], ov.get("enumerator_output_dir"))
                    elif isinstance(ov, str):
                        _add_dir_name(merged["enum"], ov)
            session_path = child / "0_session_summary.json"
            if session_path.is_file():
                try:
                    sess = json.loads(session_path.read_text(encoding="utf-8"))
                except Exception:
                    sess = {}
                if isinstance(sess, dict):
                    ov = sess.get("output_version")
                    if isinstance(ov, dict):
                        _add_dir_name(merged["enum"], ov.get("enumerator_output_dir"))
                    elif isinstance(ov, str):
                        _add_dir_name(merged["enum"], ov)
                    run = sess.get("output_version_run")
                    if isinstance(run, dict):
                        _add_dir_name(merged[kind], run.get("output_version_dir"))


def prune_disk_output_after_sim_run(
    strategy_name: str,
    sim_kind: _SimKind,
    settings: Dict[str, Any],
    *,
    protect_output_version_dir: Optional[str] = None,
) -> None:
    """单次模拟成功或 cache 维护后：按种类 prune，并跳过仍被工作台/下游引用的目录。

    ``protect_output_version_dir``：本轮刚写入的版本目录名（如 ``"5"``），避免 postprocess
    末尾 prune 删掉当前产物（CLI ``present`` 仍要读盘时尤其需要）。
    """
    sn = str(strategy_name or "").strip()
    if not sn:
        return
    root = _simulation_root(sim_kind)(sn)
    if not root.is_dir():
        return

    max_keep = resolve_max_output_versions(settings)
    refs = collect_referenced_output_version_dirs(sn)
    protected = refs.get(sim_kind, set())
    if sim_kind == "enum":
        # enum 目录常被 price/capital 的 metadata / DB 槽位引用为上游 base_output_version
        protected = set(protected) | refs["price"] | refs["capital"]
    extra = _normalize_protect_output_version_dir(protect_output_version_dir)
    if extra:
        protected = set(protected) | {extra}

    skipped = StrategyOutputVersionService.prune_simulation_versions(
        root,
        max_keep,
        protected_dir_names=frozenset(protected),
    )
    if skipped:
        logger.info(
            "prune %s for %s: skipped protected output_version dirs %s",
            sim_kind,
            sn,
            sorted(skipped),
        )


def prune_disk_outputs_for_strategy(strategy_name: str, settings: Dict[str, Any]) -> None:
    """对策略三种模拟器磁盘树各执行一次 retention（cache 命中等未写盘场景）。"""
    for kind in ("enum", "price", "capital"):
        prune_disk_output_after_sim_run(strategy_name, kind, settings)


__all__ = [
    "collect_referenced_output_version_dirs",
    "prune_disk_output_after_sim_run",
    "prune_disk_outputs_for_strategy",
    "resolve_max_output_versions",
]
