"""分层股票池：生成 dev 名单、写入 data.json、清除（供 devcli 调用）。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Tuple

from core.infra.project_context.path_manager import PathManager
from core.modules.data_manager.data_manager import DataManager
from core.modules.data_source.service.sample_stock_list import (
    invalidate_pool_cache,
    pool_csv_path,
)
from core.utils.io import csv_io
from devtools.demo_exporter.config import (
    LIST_STATUS_LABELS,
    MIN_PER_STRATUM,
    SAMPLE_RANDOM_SEED,
)
from devtools.demo_exporter.stock_pool import (
    SamplingReport,
    load_stock_universe,
    log_sampling_report,
    sample_stratified_stock_pool,
)

logger = logging.getLogger(__name__)

_DATA_JSON = PathManager.config() / "data.json"
_POOL_KEY = "use_sample_stock_list"


def _read_data_json() -> dict:
    if not _DATA_JSON.is_file():
        return {}
    return json.loads(_DATA_JSON.read_text(encoding="utf-8"))


def _write_data_json(payload: dict) -> None:
    _DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    _DATA_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def set_use_sample_stock_list(count: int | None) -> None:
    data = _read_data_json()
    if count is None:
        data.pop(_POOL_KEY, None)
    else:
        data[_POOL_KEY] = int(count)
    _write_data_json(data)
    invalidate_pool_cache()


def _rows_for_ids(universe, stock_ids):
    by_id = {r.stock_id: r for r in universe}
    rows = []
    for sid in stock_ids:
        row = by_id.get(sid)
        if row is None:
            continue
        rows.append(
            {
                "id": row.stock_id,
                "list_status": row.list_status,
                "board": row.board,
                "market": row.market,
            }
        )
    return rows


def generate_stratified_pool_files(
    *,
    count: int,
    seed: int = SAMPLE_RANDOM_SEED,
    output: Path | None = None,
    verbose: bool = False,
) -> Tuple[Path, list[str], SamplingReport]:
    if count <= 0:
        raise ValueError("count 须为正整数")

    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(message)s", force=True)

    dm = DataManager(is_verbose=False)
    dm.initialize()
    if not dm.db:
        raise RuntimeError("数据库不可用")

    universe = load_stock_universe(dm)
    stock_ids, report = sample_stratified_stock_pool(
        universe,
        target_n=count,
        seed=seed,
        min_per_stratum=MIN_PER_STRATUM,
    )
    log_sampling_report(report, status_labels=LIST_STATUS_LABELS)

    out = Path(output) if output else pool_csv_path(count)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = _rows_for_ids(universe, stock_ids)
    csv_io.write_dicts_to_csv(
        out,
        rows,
        preferred_order=["id", "list_status", "board", "market"],
    )

    meta_path = out.with_suffix(".meta.json")
    meta = {
        "sample_size": len(stock_ids),
        "target_n": count,
        "seed": seed,
        "stratification": "list_status × board × market",
        "universe_size": report.universe_size,
        "status_counts_universe": report.status_counts_universe,
        "status_counts_sample": report.status_counts_sample,
        "strata": report.stratum_rows,
        "use_sample_stock_list": count,
        "dev_pool_file": str(out),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ids_path = out.with_suffix(".ids.txt")
    ids_path.write_text("\n".join(stock_ids) + "\n", encoding="utf-8")

    logger.info("已写入 %s (%d 只)", out, len(rows))
    return out, stock_ids, report


def activate_stratified_pool(
    count: int,
    *,
    seed: int = SAMPLE_RANDOM_SEED,
    verbose: bool = False,
) -> int:
    csv_path, stock_ids, _report = generate_stratified_pool_files(
        count=count,
        seed=seed,
        verbose=verbose,
    )
    set_use_sample_stock_list(count)
    print(f"股票池已写入 data.json: {len(stock_ids)} 只", flush=True)
    print(f"  dev 名单: {csv_path}", flush=True)
    print(f"  use_sample_stock_list: {count}", flush=True)
    print("renew 将仅处理池内股票，并在 stock_list 入库后 prune 池外数据。", flush=True)
    return 0


def deactivate_stratified_pool() -> int:
    had = _POOL_KEY in _read_data_json()
    set_use_sample_stock_list(None)
    if had:
        print("已清除 data.json 的 use_sample_stock_list；renew 恢复全量 stock_list。", flush=True)
    else:
        print("data.json 未配置 use_sample_stock_list（已是全量模式）。", flush=True)
    return 0
