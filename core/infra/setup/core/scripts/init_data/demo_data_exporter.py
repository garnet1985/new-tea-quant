"""
将本地数据库导出为 ``core/infra/setup/core/steps/import_data`` 可导入的演示数据包。

- 输出 zip 命名：``data_v{core_version}_{stock_count}_{from}_{to}.zip``
- 股票池：按上市状态 × 板块 × 交易所分层抽样（见 ``stock_pool.py``）
- 表归档：``{logical_table}.tar.gz``，内含 ``{logical_table}.csv``

用法（仓库根目录）::

    python devcli.py ex                 # 显示帮助（不导出）
    python devcli.py ex --demo          # 公开安装包：约 300 只 × 默认三年窗
    python devcli.py ex --member        # 会员包：全市场 × 默认三年窗
    python devcli.py ex --full          # 全量：全市场 × 忽略日期窗
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
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
    LIST_STATUS_LABELS,
    PACKAGE_NAME_PREFIX,
    REPO_ROOT,
    SAMPLE_RANDOM_SEED,
    SYSTEM_JSON,
    TARGET_STOCK_COUNT,
    DateFilter,
    TableExportSpec,
    default_package_dir,
    package_meta_name,
    package_zip_name,
    require_package_dir,
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
    if kind == "yyyymmdd_overlap":
        from core.tables.stock.stock_st_periods.st_period_rules import (
            overlapping_window_sql,
        )

        return overlapping_window_sql(start_col=col), (end_date, start_date)
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
        "写出完成。请将 zip + meta 手动复制到官网 ntq_data/assets/install/ 并部署；"
        "本机导入：python cli.py id"
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
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    payload = {
        "core_version": core_version,
        "stock_count": stock_count,
        "start_date": start_date,
        "end_date": end_date,
        "zip_file": zip_path.name,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": digest,
        "size_bytes": zip_path.stat().st_size,
    }
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("已写入元数据 %s（sha256=%s）", meta_path.name, digest)


def _prune_stale_package_copies(package_dir: Path, keep_zip: Path) -> None:
    """删除包目录下旧的 data_v* 副本，只保留当前固定 zip。"""
    if not package_dir.is_dir():
        return
    keep = keep_zip.resolve()
    keep_name = keep_zip.name
    for pattern in ("data_v*.zip", "data_*.zip"):
        for p in package_dir.glob(pattern):
            if p.resolve() == keep:
                continue
            if p.name.startswith("example_"):
                continue
            if p.name == keep_name:
                continue
            try:
                p.unlink()
                logger.info("已删除旧数据包 %s", p.name)
            except OSError as e:
                logger.warning("无法删除 %s: %s", p.name, e)


def _warn_package_zip_conflict(package_dir: Path, target: Path) -> None:
    if not package_dir.is_dir():
        return
    others = [
        p
        for p in sorted(package_dir.glob("*.zip"))
        if p.resolve() != target.resolve() and not p.name.startswith("example_")
    ]
    if others:
        names = ", ".join(p.name for p in others)
        logger.warning(
            "演示包目录下已有其它 zip（%s）。"
            "导入时该目录只能保留 1 个非 example 包，请先移走多余文件。",
            names,
        )


_EXPORT_EPILOG = f"""
预设（必选其一才会导出；直接 ``ex`` 只显示本帮助）:
  --demo     公开安装包：约 {TARGET_STOCK_COUNT} 只分层抽样 × 默认三年窗
             （{DEFAULT_START_DATE} ~ {DEFAULT_END_DATE}）
  --member   注册会员包：全市场 × 默认三年窗（体积约数百 MB～1GB）
  --full     全量包：全市场 × 忽略日期窗（全历史；体积可达数 GB）

高级参数（可选，覆盖预设细节）:
  --start-date / --end-date / --start-quarter / --end-quarter
  --stock-count N     分层抽样数；<=0 表示全市场
  --skip-sample       不抽样（全市场）；--demo 下可用
  --no-date-filter    忽略日期窗（旧 ``--full`` 语义）；--demo/--member 下可用
  --tagged / -o / --export-dir / --tables / --format / --seed

示例:
  python devcli.py ex --demo
  python devcli.py ex --member --end-date 20261111 --end-quarter 2026Q4
  python devcli.py ex --full
""".strip()


@dataclass(frozen=True)
class ExportPlan:
    """由预设 + 可选覆盖解析出的导出计划。"""

    preset: str
    skip_sample: bool
    stock_count: int
    no_date_filter: bool
    start_date: str
    end_date: str
    start_quarter: str
    end_quarter: str


def yyyymmdd_to_quarter(yyyymmdd: str) -> str:
    y = int(yyyymmdd[:4])
    m = int(yyyymmdd[4:6])
    return f"{y}Q{(m - 1) // 3 + 1}"


def normalize_ex_argv(argv: Sequence[str] | None) -> List[str]:
    """去掉 devcli REMAINDER 常见的前导 ``--``。"""
    raw = list(argv) if argv is not None else []
    if raw and raw[0] == "--":
        return raw[1:]
    return raw


def resolve_export_plan(
    *,
    preset: str,
    start_date: Optional[str],
    end_date: Optional[str],
    start_quarter: Optional[str],
    end_quarter: Optional[str],
    stock_count: Optional[int],
    skip_sample: bool,
    no_date_filter: bool,
) -> ExportPlan:
    """将 ``--demo/--member/--full`` 解析为具体抽样与日期策略。"""
    if preset == "demo":
        use_skip = bool(skip_sample)
        count = TARGET_STOCK_COUNT if stock_count is None else int(stock_count)
        if use_skip:
            count = 0 if stock_count is None else int(stock_count)
        start = start_date or DEFAULT_START_DATE
        end = end_date or DEFAULT_END_DATE
        sq = start_quarter or DEFAULT_START_QUARTER
        eq = end_quarter or DEFAULT_END_QUARTER
        return ExportPlan(
            preset="demo",
            skip_sample=use_skip or count <= 0,
            stock_count=count,
            no_date_filter=bool(no_date_filter),
            start_date=start,
            end_date=end,
            start_quarter=sq,
            end_quarter=eq,
        )
    if preset == "member":
        count = 0 if stock_count is None else int(stock_count)
        start = start_date or DEFAULT_START_DATE
        end = end_date or DEFAULT_END_DATE
        sq = start_quarter or (
            DEFAULT_START_QUARTER if start == DEFAULT_START_DATE else yyyymmdd_to_quarter(start)
        )
        eq = end_quarter or (
            DEFAULT_END_QUARTER if end == DEFAULT_END_DATE else yyyymmdd_to_quarter(end)
        )
        return ExportPlan(
            preset="member",
            skip_sample=stock_count is None or count <= 0 or bool(skip_sample),
            stock_count=count,
            no_date_filter=bool(no_date_filter),
            start_date=start,
            end_date=end,
            start_quarter=sq,
            end_quarter=eq,
        )
    if preset == "full":
        count = 0 if stock_count is None else int(stock_count)
        start = start_date or DEFAULT_START_DATE
        end = end_date or DEFAULT_END_DATE
        sq = start_quarter or DEFAULT_START_QUARTER
        eq = end_quarter or DEFAULT_END_QUARTER
        return ExportPlan(
            preset="full",
            skip_sample=stock_count is None or count <= 0 or bool(skip_sample),
            stock_count=count,
            no_date_filter=True,
            start_date=start,
            end_date=end,
            start_quarter=sq,
            end_quarter=eq,
        )
    raise ValueError(f"未知预设: {preset}")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="导出安装/会员数据包为 setup/import_data 可导入 zip",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EXPORT_EPILOG,
    )
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument(
        "--demo",
        action="store_true",
        help=f"公开安装包：约 {TARGET_STOCK_COUNT} 只抽样 × 默认三年窗",
    )
    mode.add_argument(
        "--member",
        action="store_true",
        help="注册会员包：全市场 × 默认三年窗",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="全量包：全市场 × 忽略日期窗（全历史）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="输出 zip 完整路径（默认 userspace/.ntq/packages/{demo|member|full}/data_*.zip）",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        help="输出目录（默认 userspace/.ntq/packages/{demo|member|full}/；与 -o 二选一）",
    )
    parser.add_argument(
        "--tagged",
        action="store_true",
        help="除固定 data_*.zip 外，再写一份 data_v{version}_{n}_{from}_{to}.zip（勿提交 Git）",
    )
    parser.add_argument("--tables", help="逗号分隔逻辑表名，覆盖 config.EXPORT_TABLES")
    parser.add_argument(
        "--no-date-filter",
        action="store_true",
        help="忽略日期窗（旧 --full 语义；仍按股票池过滤）。--full 预设已隐含此行为",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help=f"时序窗起点 YYYYMMDD（默认 {DEFAULT_START_DATE}）",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help=f"时序窗终点 YYYYMMDD（默认 {DEFAULT_END_DATE}）",
    )
    parser.add_argument(
        "--start-quarter",
        default=None,
        help=f"季度窗起点（默认 {DEFAULT_START_QUARTER}）",
    )
    parser.add_argument(
        "--end-quarter",
        default=None,
        help=f"季度窗终点（默认 {DEFAULT_END_QUARTER}）",
    )
    parser.add_argument(
        "--stock-count",
        type=int,
        default=None,
        help=f"分层抽样目标股票数（--demo 默认 {TARGET_STOCK_COUNT}；<=0 表示全市场）",
    )
    parser.add_argument("--seed", type=int, default=SAMPLE_RANDOM_SEED, help="抽样随机种子")
    parser.add_argument(
        "--skip-sample",
        action="store_true",
        help="不抽样，导出全市场股票相关表（--member/--full 已隐含）",
    )
    parser.add_argument(
        "--format",
        choices=["tar.gz", "zip"],
        default="tar.gz",
        help="单表归档格式",
    )
    return parser


def _selected_preset(args: argparse.Namespace) -> Optional[str]:
    if args.demo:
        return "demo"
    if args.member:
        return "member"
    if args.full:
        return "full"
    return None


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = _build_arg_parser()
    args = parser.parse_args(normalize_ex_argv(argv))

    preset = _selected_preset(args)
    if preset is None:
        parser.print_help()
        return 0

    plan = resolve_export_plan(
        preset=preset,
        start_date=args.start_date,
        end_date=args.end_date,
        start_quarter=args.start_quarter,
        end_quarter=args.end_quarter,
        stock_count=args.stock_count,
        skip_sample=bool(args.skip_sample),
        no_date_filter=bool(args.no_date_filter),
    )

    start_date = _validate_yyyymmdd("--start-date", plan.start_date)
    end_date = _validate_yyyymmdd("--end-date", plan.end_date)
    start_quarter = _validate_quarter("--start-quarter", plan.start_quarter)
    end_quarter = _validate_quarter("--end-quarter", plan.end_quarter)
    if start_date > end_date:
        raise SystemExit(f"日期区间非法: {start_date} > {end_date}")
    if start_quarter > end_quarter:
        raise SystemExit(f"季度区间非法: {start_quarter} > {end_quarter}")
    core_version = read_core_version()

    logger.info(
        "导出预设=%s skip_sample=%s stock_count=%s no_date_filter=%s window=%s..%s",
        plan.preset,
        plan.skip_sample,
        plan.stock_count,
        plan.no_date_filter,
        start_date,
        end_date,
    )

    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    dm.initialize()
    if not dm.db:
        logger.error("数据库不可用")
        return 1

    use_full_universe = plan.skip_sample or plan.stock_count <= 0
    if use_full_universe:
        stock_model = dm.get_table("sys_data_stock_list")
        if stock_model is None:
            logger.error("未注册 sys_data_stock_list")
            return 1
        stock_ids = sorted(r["id"] for r in stock_model.load("1=1") if r.get("id"))
        logger.info("全市场：共 %d 只股票（未分层抽样）", len(stock_ids))
    else:
        universe = load_stock_universe(dm)
        stock_ids, report = sample_stratified_stock_pool(
            universe,
            target_n=plan.stock_count,
            seed=args.seed,
        )
        log_sampling_report(report, status_labels=LIST_STATUS_LABELS)

    tagged_name = package_zip_basename(
        core_version=core_version,
        stock_count=len(stock_ids),
        start_date=start_date,
        end_date=end_date,
    )

    try:
        if args.output:
            output_zip = args.output
            package_dir = output_zip.parent
            package_dir.mkdir(parents=True, exist_ok=True)
            write_package_sidecar = False
        else:
            package_dir = (
                Path(args.export_dir).expanduser().resolve()
                if args.export_dir
                else require_package_dir(preset)
            )
            package_dir.mkdir(parents=True, exist_ok=True)
            output_zip = package_dir / package_zip_name(preset)
            write_package_sidecar = (
                package_dir.resolve() == default_package_dir(preset).resolve()
            )
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    if write_package_sidecar:
        _warn_package_zip_conflict(package_dir, output_zip)

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
            full=plan.no_date_filter,
            start_date=start_date,
            end_date=end_date,
            start_quarter=start_quarter,
            end_quarter=end_quarter,
            archive_format=args.format,
        )
        if write_package_sidecar:
            _write_data_meta(
                meta_path=package_dir / package_meta_name(preset),
                core_version=core_version,
                stock_count=len(stock_ids),
                start_date=start_date,
                end_date=end_date,
                zip_path=output_zip,
            )
            _prune_stale_package_copies(package_dir, output_zip)
            if args.tagged:
                tagged_path = package_dir / tagged_name
                shutil.copy2(output_zip, tagged_path)
                logger.info("已额外写入带版本号文件 %s（勿提交 Git）", tagged_name)
            logger.info(
                "请将 %s 与 %s 手动复制到官网 ntq_data/assets/install/ 并部署",
                package_zip_name(preset),
                package_meta_name(preset),
            )
    except Exception as e:
        logger.error("%s", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
