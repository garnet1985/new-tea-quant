"""把战役各格的价格层机会铺平，做单笔 XGB + SHAP。

格子对照仍走 overlays / matrix；这里只吃 unique version 的投资明细。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.analysis import Analysis
from core.modules.strategy.core.engines.analyzer.steps.analyze.data.outcome import (
    StepOutcomeRegistry,
)
from core.modules.strategy.core.engines.analyzer.steps.prepare.prepare import PrepareStep
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

from .cells import AttributionCell
from .contrasts import KnobContrasts

logger = logging.getLogger(__name__)

_READY = frozenset({"hit", "simulated"})
_MIN_SAMPLES = 80
_MIN_FEATURES = 2
_MIN_PER_FEATURE = 10
_MAX_OPPORTUNITY = 8
_SKIP_CAPTURE = frozenset(
    {
        "date",
        "entity_id",
        "investment_id",
        "open",
        "close",
        "high",
        "low",
        "pre_close",
        "volume",
        "amount",
        "adj_factor",
        "price_change_delta",
        "price_change_rate_delta",
    }
)
_KEEP_LAST = frozenset(
    {
        "rsi",
        "rsi14",
        "pe_percentile",
        "pe",
        "pe_ttm",
        "pb",
        "ps",
        "ps_ttm",
        "macd",
        "macd_hist",
        "hist",
        "turnover_rate",
        "volume_ratio",
        "netprofit_yoy",
    }
)


class TradesStep:
    """战役 unique version → 单笔特征矩阵 → 二分类 SHAP。"""

    @classmethod
    def run(
        cls,
        folder: Path,
        unique_cells: Sequence[AttributionCell],
        executed: Mapping[str, Any],
    ) -> Dict[str, Any]:
        knob_paths = KnobContrasts.union_paths(
            cell.overlay for cell in unique_cells
        )
        rows, versions = cls._load_rows(folder, unique_cells, executed, knob_paths)
        return cls.from_rows(rows, versions=versions, knob_paths=knob_paths)

    @classmethod
    def from_rows(
        cls,
        rows: Sequence[Mapping[str, Any]],
        *,
        versions: Optional[Sequence[str]] = None,
        knob_paths: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        n = len(rows)
        names, kinds = cls._feature_spec(rows, knob_paths or [])
        if len(names) < _MIN_FEATURES:
            return {
                "status": "skipped",
                "reason": "insufficient_varying_fields",
                "n": n,
                "n_versions": len(list(versions or [])),
                "features": names,
            }
        param_names = {
            name for name, kind in zip(names, kinds) if kind == "parameter"
        }
        matrix: List[List[float]] = []
        wins: List[bool] = []
        groups: List[str] = []
        for row in rows:
            vector = cls._row_vector(row, names, param_names)
            if vector is None:
                continue
            win = row.get("win")
            if win is None:
                continue
            matrix.append(vector)
            wins.append(bool(win))
            groups.append(str(row.get("group") or "").strip())
        fitted = Analysis.ML.xgb_win_classifier(
            matrix, names, wins, min_samples=_MIN_SAMPLES, groups=groups
        )
        n_param = sum(1 for kind in kinds if kind == "parameter")
        n_opp = len(kinds) - n_param
        out = dict(fitted)
        out["n_versions"] = len(list(versions or []))
        out["n_raw"] = n
        out["features"] = names
        out["feature_kinds"] = [
            {"feature": name, "kind": kind} for name, kind in zip(names, kinds)
        ]
        out["n_parameter"] = n_param
        out["n_opportunity"] = n_opp
        if out.get("status") in {"ok", "partial"}:
            out["overview"] = {
                "n": out.get("n"),
                "n_versions": out.get("n_versions"),
                "n_features": out.get("n_features"),
                "n_parameter": n_param,
                "n_opportunity": n_opp,
                "n_train": out.get("n_train"),
                "n_test": out.get("n_test"),
                "auc": (out.get("metrics") or {}).get("auc"),
                "auc_train": (out.get("metrics") or {}).get("auc_train"),
                "auc_test": (out.get("metrics") or {}).get("auc_test"),
                "accuracy": (out.get("metrics") or {}).get("accuracy"),
                "split": out.get("split"),
            }
        return out

    @classmethod
    def _load_rows(
        cls,
        folder: Path,
        unique_cells: Sequence[AttributionCell],
        executed: Mapping[str, Any],
        knob_paths: Sequence[str],
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        by_index = {
            int(row["index"]): row
            for row in executed.get("cells") or []
            if isinstance(row, dict) and "index" in row
        }
        rows: List[Dict[str, Any]] = []
        versions: List[str] = []
        outcome = StepOutcomeRegistry.get("price")
        for cell in unique_cells:
            raw = by_index.get(cell.index) or {}
            if str(raw.get("status") or "") not in _READY:
                continue
            vid = str(raw.get("version_id") or "").strip()
            if not vid:
                continue
            knobs = cls._version_knobs(folder, vid, cell, knob_paths)
            try:
                store = ArtifactStore.resolve(
                    folder, kind=SimulateKind.PRICE_FACTOR, version_id=vid
                )
                payload = PrepareStep(store).build()
            except Exception:
                logger.info("trades skip version %s: prepare failed", vid)
                continue
            versions.append(vid)
            for entity in payload.get("entities") or []:
                if not isinstance(entity, dict):
                    continue
                for investment in entity.get("investments") or []:
                    if not isinstance(investment, dict):
                        continue
                    roi = Analysis.Classical.coerce_float(
                        _nested(investment, outcome.roi_field)
                    )
                    if roi is None:
                        continue
                    capture = investment.get("capture")
                    if not isinstance(capture, dict):
                        capture = {}
                    rows.append(
                        {
                            "version_id": vid,
                            "knobs": knobs,
                            "capture": capture,
                            "group": _trade_group(entity, investment),
                            "roi": roi,
                            "win": roi > 0,
                        }
                    )
        return rows, versions

    @classmethod
    def _version_knobs(
        cls,
        folder: Path,
        version_id: str,
        cell: AttributionCell,
        knob_paths: Sequence[str],
    ) -> Dict[str, Any]:
        source: Any = cell.effective
        disk = VersionMetaStore.read_effective_settings(
            ArtifactStore.simulations_root(folder), version_id
        )
        if disk:
            source = disk
        return KnobContrasts.read(source, knob_paths)

    @classmethod
    def _feature_spec(
        cls,
        rows: Sequence[Mapping[str, Any]],
        knob_paths: Sequence[str],
    ) -> Tuple[List[str], List[str]]:
        names: List[str] = []
        kinds: List[str] = []
        for path in knob_paths:
            series = [
                KnobContrasts.scalar((row.get("knobs") or {}).get(path))
                for row in rows
            ]
            if cls._knob_varies(series):
                names.append(str(path))
                kinds.append("parameter")
        capture_keys: List[str] = []
        seen = set()
        for row in rows:
            capture = row.get("capture") if isinstance(row.get("capture"), dict) else {}
            for key in capture:
                text = str(key)
                if text in seen or not _keep_opportunity(text):
                    continue
                seen.add(text)
                capture_keys.append(text)
        opp: List[Tuple[str, float]] = []
        for key in capture_keys:
            series = [
                Analysis.Classical.coerce_float((row.get("capture") or {}).get(key))
                for row in rows
            ]
            if not cls._is_varying(series):
                continue
            opp.append((key, _variance(series)))
        opp.sort(key=lambda item: item[1], reverse=True)
        for key, _var in opp[:_MAX_OPPORTUNITY]:
            names.append(key)
            kinds.append("opportunity")
        n = len(rows)
        while (
            names
            and n // max(len(names), 1) < _MIN_PER_FEATURE
            and any(kind == "opportunity" for kind in kinds)
        ):
            for i in range(len(kinds) - 1, -1, -1):
                if kinds[i] == "opportunity":
                    names.pop(i)
                    kinds.pop(i)
                    break
        return names, kinds

    @staticmethod
    def _knob_varies(series: Sequence[Optional[float]]) -> bool:
        levels = set()
        for item in series:
            if item is None:
                levels.add("off")
            else:
                levels.add(round(float(item), 8))
        return len(levels) >= 2

    @staticmethod
    def _is_varying(series: Sequence[Optional[float]]) -> bool:
        values = [item for item in series if item is not None]
        if len(values) < 8:
            return False
        uniq = {round(float(item), 8) for item in values}
        return len(uniq) >= 2

    @classmethod
    def _row_vector(
        cls,
        row: Mapping[str, Any],
        names: Sequence[str],
        param_names: Sequence[str],
    ) -> Optional[List[float]]:
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        capture = row.get("capture") if isinstance(row.get("capture"), dict) else {}
        params = set(param_names)
        vector: List[float] = []
        for name in names:
            if name in params:
                number = KnobContrasts.scalar(knobs.get(name))
            else:
                number = Analysis.Classical.coerce_float(capture.get(name))
            if number is None:
                vector.append(float("nan"))
            else:
                vector.append(float(number))
        return vector


def _nested(row: Mapping[str, Any], dotted: str) -> Any:
    current: Any = row
    for part in str(dotted or "").split("."):
        if not part:
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _trade_group(entity: Mapping[str, Any], investment: Mapping[str, Any]) -> str:
    """同一股票同一买入日，跨 version 算同一笔，训练测试不能拆开。"""
    entity_id = str(entity.get("entity_id") or "").strip()
    enter = str(_nested(investment, "engine.enter_date") or "").strip()
    if entity_id and enter:
        return f"{entity_id}|{enter}"
    inv_id = str(investment.get("investment_id") or "").strip()
    if entity_id and inv_id:
        return f"{entity_id}|{inv_id}"
    return ""


def _keep_opportunity(key: str) -> bool:
    text = str(key or "")
    last = text.split(".")[-1]
    if last in _SKIP_CAPTURE:
        return False
    if last.endswith("_date") or last.endswith("_share") or "market_value" in last:
        return False
    if last.startswith("rsi") or last.startswith("macd") or last.startswith("pe"):
        return True
    if last in _KEEP_LAST:
        return True
    if "." not in text:
        return last not in _SKIP_CAPTURE
    return False


def _variance(series: Sequence[Optional[float]]) -> float:
    values = [float(item) for item in series if item is not None]
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((item - mean) ** 2 for item in values) / len(values)
