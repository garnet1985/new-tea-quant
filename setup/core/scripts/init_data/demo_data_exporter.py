"""
将本地数据库导出为 ``setup/core/steps/import_data`` 可导入的演示数据包。

- 输出 zip 命名：``data_v{core_version}_{stock_count}_{from}_{to}.zip``
- 股票池：按上市状态 × 板块 × 交易所分层抽样（见 ``stock_pool.py``）
- 表归档：``{logical_table}.tar.gz``，内含 ``{logical_table}.csv``

用法（仓库根目录）::

    python devcli.py ex
    python -m setup.core.scripts.init_data --help
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .config import (
    DEFAULT_END_DATE,
    DEFAULT_END_QUARTER,
    DEFAULT_START_DATE,
    DEFAULT_START_QUARTER,
    EXCLUDED_GENERATED_TABLES,
    EXPORT_TABLES,
    GIT_DATA_META_NAME,
    GIT_DATA_ZIP_NAME,
    INIT_DATA_DIR,
    LIST_STATUS_LABELS,
    PACKAGE_NAME_PREFIX,
    REPO_ROOT,
    SAMPLE_RANDOM_SEED,
    SYSTEM_JSON,
    TARGET_STOCK_COUNT,
    DateFilter,
    TableExportSpec,
)
from .stock_pool import (
    load_stock_universe,
    log_sampling_report,
    sample_stratified_stock_pool,
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)


def read_core_version() -> str:
    if not SYSTEM_JSON.is_file():
        raise RuntimeError(f"缺少 {SYSTEM_JSON}")
    data = json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))
    version = str(data.get("version", "")).strip()
    if not version:
        raise RuntimeError("core/system.json 中未配置 version")
    return version if version.startswith("v") else f"v{version}"


def package_zip_basename(*, core_version: str, stock_count: int, start_date: str, end_date: str) -> str:
    ver = core_version if core_version.startswith("v") else f"v{core_version}"
    return f"{PACKAGE_NAME_PREFIX}_{ver}_{stock_count}_{start_date}_{end_date}.zip"


def _validate_yyyymmdd(label: str, value: str) -> str:
    if not re.fullmatch(r"\d{8}", value):
        raise SystemExit(f"{label} 格式错误: {value}，应为 YYYYMMDD")
    return value


def _validate_quarter(label: str, value: str) -> str:
    if not re.fullmatch(r"\d{4}Q[1-4]", value):
        raise SystemExit(f"{label} 格式错误: {value}，应为 YYYYQ[1-4]")
    return value


def build_date_condition(
    date_filter: DateFilter,
    *,
    full: bool,
    start_date: str,
    end_date: str,
    start_quarter: str,
    end_quarter: str,
) -> Tuple[str, tuple]:
    if full or not date_filter:
        return "1=1", ()
    col, kind = date_filter
    if kind == "yyyymmdd":
        return f"{col} >= %s AND {col} <= %s", (start_date, end_date)
    if kind == "quarter":
        return f"{col} >= %s AND {col} <= %s", (start_quarter, end_quarter)
    raise ValueError(f"未知日期过滤类型: {kind}")


def build_stock_condition(column: str, stock_ids: Sequence[str]) -> Tuple[str, tuple]:
    if not stock_ids:
        return "1=0", ()
    placeholders = ", ".join(["%s"] * len(stock_ids))
    return f"{column} IN ({placeholders})", tuple(stock_ids)


def combine_conditions(*parts: Tuple[str, tuple]) -> Tuple[str, tuple]:
    conds: List[str] = []
    params: List = []
    for cond, ps in parts:
        if cond and cond != "1=1":
            conds.append(f"({cond})")
            params.extend(ps)
    if not conds:
        return "1=1", ()
    return " AND ".join(conds), tuple(params)


def build_table_export_condition(
    spec: TableExportSpec,
    *,
    stock_ids: Sequence[str],
    full: bool,
    start_date: str,
    end_date: str,
    start_quarter: str,
    end_quarter: str,
) -> Tuple[str, tuple]:
    parts: List[Tuple[str, tuple]] = [
        build_date_condition(
            spec.date_filter,
            full=full,
            start_date=start_date,
            end_date=end_date,
            start_quarter=start_quarter,
            end_quarter=end_quarter,
        )
    ]
    if spec.stock_column and stock_ids:
        parts.append(build_stock_condition(spec.stock_column, stock_ids))
    return combine_conditions(*parts)


def _resolve_tables(explicit: Optional[List[str]]) -> Dict[str, TableExportSpec]:
    if not explicit:
        return dict(EXPORT_TABLES)
    out: Dict[str, TableExportSpec] = {}
    for name in explicit:
        key = name.strip()
        if not key:
            continue
        if key in EXCLUDED_GENERATED_TABLES:
            logger.warning("跳过运行时/生成表（不导出）: %s", key)
            continue
        if key not in EXPORT_TABLES:
            logger.warning("未在 config.EXPORT_TABLES 中定义，将仅按全表/日期导出: %s", key)
            out[key] = TableExportSpec()
        else:
            out[key] = EXPORT_TABLES[key]
    return out


def export_demo_data_package(
    *,
    output_zip: Path,
    tables: Dict[str, TableExportSpec],
    stock_ids: Sequence[str],
    full: bool = False,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    start_quarter: str = DEFAULT_START_QUARTER,
    end_quarter: str = DEFAULT_END_QUARTER,
    archive_format: str = "tar.gz",
) -> Path:
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()
    if not dm.db:
        raise RuntimeError("DataManager 未初始化或数据库不可用")

    output_zip = output_zip.resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    exported: List[Path] = []
    skipped: List[str] = []

    with tempfile.TemporaryDirectory(prefix="ntq_demo_export_") as tmp:
        staging = Path(tmp)
        for table_name, spec in tables.items():
            if table_name in EXCLUDED_GENERATED_TABLES:
                logger.warning("跳过运行时/生成表（不导出）: %s", table_name)
                skipped.append(table_name)
                continue
            model = dm.get_table(table_name)
            if model is None:
                logger.warning("表未注册，跳过: %s", table_name)
                skipped.append(table_name)
                continue

            condition, params = build_table_export_condition(
                spec,
                stock_ids=stock_ids,
                full=full,
                start_date=start_date,
                end_date=end_date,
                start_quarter=start_quarter,
                end_quarter=end_quarter,
            )
            if spec.stock_column and stock_ids:
                scope = f"股票池 {len(stock_ids)} 只"
            else:
                scope = "全市场"
            if spec.date_filter and not full:
                logger.info("导出 %s（%s, 日期窗）", table_name, scope)
            else:
                logger.info("导出 %s（%s, 全量日期）", table_name, scope)

            paths = model.export_data(
                staging,
                archive_format=archive_format,
                condition=condition,
                params=params,
            )
            exported.extend(paths)

        if not exported:
            raise RuntimeError(
                "没有导出任何表归档。"
                + (f" 跳过未注册: {', '.join(skipped)}" if skipped else "")
            )

        if output_zip.exists():
            output_zip.unlink()
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for arch in sorted(staging.glob("*.tar.gz")):
                zf.write(arch, arcname=arch.name)
            for arch in sorted(staging.glob("*.zip")):
                if arch.name == output_zip.name:
                    continue
                zf.write(arch, arcname=arch.name)

    logger.info(
        "演示数据包已写入 %s（%d 个表归档%s）",
        output_zip,
        len(exported),
        f"，跳过 {len(skipped)} 张未注册表" if skipped else "",
    )
    logger.info(
        "导入：将 zip 单独放入 setup/init_data/ 后执行 "
        "python setup/core/steps/import_data/install.py"
    )
    return output_zip


def _write_data_meta(
    *,
    meta_path: Path,
    core_version: str,
    stock_count: int,
    start_date: str,
    end_date: str,
    zip_path: Path,
) -> None:
    payload = {
        "core_version": core_version,
        "stock_count": stock_count,
        "start_date": start_date,
        "end_date": end_date,
        "zip_file": zip_path.name,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("已写入元数据 %s", meta_path.name)


def _prune_stale_init_data_packages(keep_zip: Path) -> None:
    """删除 init_data 下旧的 data_v* 等副本，只保留固定 data_demo.zip（及 example_*）。"""
    if not INIT_DATA_DIR.is_dir():
        return
    keep = keep_zip.resolve()
    for pattern in ("data_v*.zip", "data_*.zip"):
        for p in INIT_DATA_DIR.glob(pattern):
            if p.resolve() == keep:
                continue
            if p.name.startswith("example_"):
                continue
            if p.name == GIT_DATA_ZIP_NAME:
                continue
            try:
                p.unlink()
                logger.info("已删除旧数据包 %s", p.name)
            except OSError as e:
                logger.warning("无法删除 %s: %s", p.name, e)


def _warn_init_data_zip_conflict(target: Path) -> None:
    if not INIT_DATA_DIR.is_dir():
        return
    others = [
        p
        for p in sorted(INIT_DATA_DIR.glob("*.zip"))
        if p.resolve() != target.resolve() and not p.name.startswith("example_")
    ]
    if others:
        names = ", ".join(p.name for p in others)
        logger.warning(
            "setup/init_data/ 下已有其它 zip（%s）。"
            "安装导入时该目录只能保留 1 个非 example 包，请先移走多余文件。",
            names,
        )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="导出分层抽样演示数据为 setup/import_data 可导入 zip"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=f"输出 zip 完整路径（默认 {INIT_DATA_DIR.relative_to(REPO_ROOT)}/{GIT_DATA_ZIP_NAME}）",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        help=f"输出目录（默认 {INIT_DATA_DIR.relative_to(REPO_ROOT)}/；与 -o 二选一）",
    )
    parser.add_argument(
        "--tagged",
        action="store_true",
        help="除 data_demo.zip 外，再写一份 data_v{version}_{n}_{from}_{to}.zip（勿提交 Git）",
    )
    parser.add_argument("--tables", help="逗号分隔逻辑表名，覆盖 config.EXPORT_TABLES")
    parser.add_argument("--full", action="store_true", help="忽略日期窗（仍按股票池过滤）")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--start-quarter", default=DEFAULT_START_QUARTER)
    parser.add_argument("--end-quarter", default=DEFAULT_END_QUARTER)
    parser.add_argument(
        "--stock-count",
        type=int,
        default=TARGET_STOCK_COUNT,
        help="分层抽样目标股票数；<= 0 表示全市场（与 --skip-sample 相同）",
    )
    parser.add_argument("--seed", type=int, default=SAMPLE_RANDOM_SEED, help="抽样随机种子")
    parser.add_argument(
        "--skip-sample",
        action="store_true",
        help="不抽样，导出 config 中全部股票相关表（慎用，体积大）",
    )
    parser.add_argument(
        "--format",
        choices=["tar.gz", "zip"],
        default="tar.gz",
        help="单表归档格式",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _build_arg_parser().parse_args(list(argv) if argv is not None else None)

    start_date = _validate_yyyymmdd("--start-date", args.start_date)
    end_date = _validate_yyyymmdd("--end-date", args.end_date)
    start_quarter = _validate_quarter("--start-quarter", args.start_quarter)
    end_quarter = _validate_quarter("--end-quarter", args.end_quarter)
    if start_date > end_date:
        raise SystemExit(f"日期区间非法: {start_date} > {end_date}")
    if start_quarter > end_quarter:
        raise SystemExit(f"季度区间非法: {start_quarter} > {end_quarter}")
    core_version = read_core_version()

    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()
    if not dm.db:
        logger.error("数据库不可用")
        return 1

    use_full_universe = args.skip_sample or args.stock_count <= 0
    if use_full_universe:
        stock_model = dm.get_table("sys_stock_list")
        if stock_model is None:
            logger.error("未注册 sys_stock_list")
            return 1
        stock_ids = sorted(r["id"] for r in stock_model.load("1=1") if r.get("id"))
        logger.info("全市场：共 %d 只股票（未分层抽样）", len(stock_ids))
    else:
        universe = load_stock_universe(dm)
        stock_ids, report = sample_stratified_stock_pool(
            universe,
            target_n=args.stock_count,
            seed=args.seed,
        )
        log_sampling_report(report, status_labels=LIST_STATUS_LABELS)

    tagged_name = package_zip_basename(
        core_version=core_version,
        stock_count=len(stock_ids),
        start_date=start_date,
        end_date=end_date,
    )

    if args.output:
        output_zip = args.output
        write_init_data = False
    else:
        out_dir = args.export_dir or INIT_DATA_DIR
        output_zip = out_dir / GIT_DATA_ZIP_NAME
        write_init_data = out_dir.resolve() == INIT_DATA_DIR.resolve()

    if write_init_data:
        _warn_init_data_zip_conflict(output_zip)

    explicit_tables = None
    if args.tables:
        explicit_tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    tables = _resolve_tables(explicit_tables)
    if not tables:
        raise SystemExit("没有可导出的表")

    try:
        export_demo_data_package(
            output_zip=output_zip,
            tables=tables,
            stock_ids=stock_ids,
            full=args.full,
            start_date=start_date,
            end_date=end_date,
            start_quarter=start_quarter,
            end_quarter=end_quarter,
            archive_format=args.format,
        )
        if write_init_data:
            _write_data_meta(
                meta_path=INIT_DATA_DIR / GIT_DATA_META_NAME,
                core_version=core_version,
                stock_count=len(stock_ids),
                start_date=start_date,
                end_date=end_date,
                zip_path=output_zip,
            )
            _prune_stale_init_data_packages(output_zip)
            if args.tagged:
                tagged_path = INIT_DATA_DIR / tagged_name
                shutil.copy2(output_zip, tagged_path)
                logger.info("已额外写入带版本号文件 %s（勿提交 Git）", tagged_name)
            logger.info(
                "提交 Git 时请只 add %s 与 %s；若曾提交过 data_v*.zip，执行: "
                "git rm --cached setup/init_data/data_v*.zip",
                GIT_DATA_ZIP_NAME,
                GIT_DATA_META_NAME,
            )
    except Exception as e:
        logger.error("%s", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
