"""从策略回测产物加载 (date, value) 点列。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from core.modules.strategy.core.services.artifacts.consts import (
    EQUITY_CURVE_FILE,
    PRICE_INVESTMENTS_SUFFIX,
)
from core.modules.strategy.core.services.artifacts.store import (
    ArtifactStore,
    PriceFactorStore,
)


class StrategySimLoadError(ValueError):
    """回测产物缺失或无法解析（装载期硬失败）。"""


def load_strategy_sim_points(
    item: Mapping[str, Any],
    *,
    start_date: str = "",
    end_date: str = "",
    resolve_folder=None,
) -> Tuple[List[Tuple[str, float]], Dict[str, Any]]:
    """返回 ``(points, resolved_meta)``；失败抛 ``StrategySimLoadError``。"""
    strategy_key = str(item.get("strategy_key") or "").strip()
    version = str(item.get("version") or "").strip() or "latest"
    layer = str(item.get("layer") or "").strip()
    metric = str(item.get("metric") or "").strip()
    entity_id = str(item.get("entity_id") or "").strip()
    if not strategy_key or not layer or not metric:
        raise StrategySimLoadError(
            "strategy_sim 缺少 strategy_key/layer/metric"
            "（strategy_key 填 meta.key，也可用相对路径）"
        )

    folder = _resolve_strategy_folder(strategy_key, resolve_folder=resolve_folder)
    store, resolved_vid = _open_layer_store(folder, layer=layer, version=version)

    if layer == "portfolio" and metric == "equity":
        points = _load_portfolio_equity(store, start_date=start_date, end_date=end_date)
    elif layer == "price" and metric == "cum_exit_roi":
        if not isinstance(store, PriceFactorStore):
            store = PriceFactorStore.at(store.output_dir, version_id=store.version_id)
        points = _load_price_cum_exit_roi(
            store, entity_id=entity_id, start_date=start_date, end_date=end_date
        )
    else:
        raise StrategySimLoadError(f"不支持 layer={layer} metric={metric}")

    if not points:
        raise StrategySimLoadError(
            f"strategy_sim 无有效点: strategy_key={strategy_key} "
            f"version={resolved_vid} layer={layer} metric={metric}"
            + (f" entity_id={entity_id}" if entity_id else "")
            + "（请确认已跑对应回测层且有数据）"
        )

    meta = {
        "strategy_key": strategy_key,
        "version": version,
        "resolved_version": resolved_vid,
        "layer": layer,
        "metric": metric,
        "entity_id": entity_id,
        "output_dir": str(store.output_dir),
    }
    return points, meta


def _resolve_strategy_folder(strategy_key: str, *, resolve_folder=None) -> Path:
    """``strategy_key``：优先按策略 ``meta.key`` 解析，也接受相对路径 id。"""
    if resolve_folder is not None:
        folder = Path(resolve_folder(strategy_key))
    else:
        from core.modules.strategy import Strategy

        try:
            folder = Path(Strategy.resolve_folder(strategy_key))
        except Exception as exc:
            raise StrategySimLoadError(
                f"未找到策略 strategy_key={strategy_key!r}（{exc}）"
            ) from exc
    if not folder.is_dir():
        raise StrategySimLoadError(f"策略目录不存在: {folder}")
    return folder


def _open_layer_store(
    folder: Path,
    *,
    layer: str,
    version: str,
) -> Tuple[ArtifactStore, str]:
    """只读定位层目录；用 ``at`` 而非 ``open``，避免强依赖 runtime_env。"""
    kind = "portfolio" if layer == "portfolio" else "price"
    tip = "so" if kind == "portfolio" else "sp"
    vid = str(version or "").strip() or "latest"
    if vid == "latest":
        store = ArtifactStore.latest(folder, kind=kind)
        if store is None:
            raise StrategySimLoadError(
                f"策略无可用 {kind} 回测版本（latest）：{folder}；请先跑 {tip}"
            )
        return store, str(store.version_id)

    impl = ArtifactStore.for_kind(kind)
    root = impl.simulations_root(folder)
    output_dir = root / vid / impl.step_dir_name()
    if not output_dir.is_dir():
        raise StrategySimLoadError(
            f"策略 version={vid} 缺少 {kind} 层目录：{output_dir}；请先跑 {tip}"
        )
    return impl.at(output_dir, version_id=vid), vid


def _load_portfolio_equity(
    store: ArtifactStore,
    *,
    start_date: str,
    end_date: str,
) -> List[Tuple[str, float]]:
    path = store.file("equity_curve")
    if not path.is_file():
        # named file constant fallback
        path = store.output_dir / EQUITY_CURVE_FILE
    if not path.is_file():
        raise StrategySimLoadError(
            f"缺少权益曲线: {path}（请确认 portfolio 已保存 equity_curve）"
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StrategySimLoadError(f"无法解析 equity_curve: {path}（{exc}）") from exc
    if not isinstance(raw, list):
        raise StrategySimLoadError(f"equity_curve 应为 list: {path}")

    start = str(start_date or "").strip()
    end = str(end_date or "").strip()
    out: List[Tuple[str, float]] = []
    for row in raw:
        if not isinstance(row, Mapping):
            continue
        day = str(row.get("date") or "").strip()
        if not day:
            continue
        if start and day < start:
            continue
        if end and day > end:
            continue
        value = _as_float(row.get("equity"))
        if value is None:
            continue
        out.append((day, value))
    out.sort(key=lambda item: item[0])
    return out


def _load_price_cum_exit_roi(
    store: PriceFactorStore,
    *,
    entity_id: str,
    start_date: str,
    end_date: str,
) -> List[Tuple[str, float]]:
    if entity_id:
        path = store.entity_file(entity_id, PRICE_INVESTMENTS_SUFFIX)
        if not path.is_file():
            raise StrategySimLoadError(
                f"缺少单票 investments: {path}（entity_id={entity_id}）"
            )
        entity_ids = [entity_id]
    else:
        entity_ids = store.list_investment_entities()
        if not entity_ids:
            raise StrategySimLoadError(
                f"price 层无任何 investments CSV: {store.entities_dir()}"
            )

    # exit_date -> sum roi that day
    by_day: Dict[str, float] = {}
    for eid in entity_ids:
        for row in store.investments(eid):
            day = str(getattr(row, "exit_date", "") or "").strip()
            if not day or day in ("", "0", "None"):
                continue
            roi = _as_float(getattr(row, "roi", None))
            if roi is None:
                continue
            by_day[day] = by_day.get(day, 0.0) + float(roi)

    start = str(start_date or "").strip()
    end = str(end_date or "").strip()
    days = sorted(by_day)
    cum = 0.0
    out: List[Tuple[str, float]] = []
    for day in days:
        if start and day < start:
            continue
        if end and day > end:
            continue
        cum += by_day[day]
        out.append((day, cum))
    return out


def _as_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


__all__ = ["load_strategy_sim_points", "StrategySimLoadError"]
