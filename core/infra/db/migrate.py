"""
数据库 schema 升级 CLI（由 ``userspace/updater`` 子进程调用）。

用法::

    PYTHONPATH=<repo_root> python -m core.infra.db.migrate apply \\
        --pre-mirror-snapshot userspace/.ntq/update/cache/pre_mirror_core_table_schemas.json

    python -m core.infra.db.migrate plan --pre-mirror-snapshot <path>   # 仅生成 plan，不连库写 DDL
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from core.infra.db.db_manager import DatabaseManager
from core.infra.db.migration.execution_plan import MigrationPlanError, ordered_plan
from core.infra.db.migration.introspection import introspect_database
from core.infra.db.migration.plan_prune import prune_plan_for_database
from core.infra.db.migration.runner import (
    build_migration_plan,
    default_pre_mirror_snapshot_path,
    load_current_table_schemas,
    load_schemas_from_snapshot,
    run_schema_migration,
)

logger = logging.getLogger(__name__)


def _write_migration_result_json(path: Path, result) -> None:
    """写入供 updater 读取的摘要 JSON。"""
    payload = {
        "skipped_reason": result.skipped_reason,
        "applied": result.applied,
        "step_count": result.step_count,
        "old_schema_count": result.old_schema_count,
        "new_schema_count": result.new_schema_count,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _resolve_snapshot_path(args: argparse.Namespace) -> Path:
    if args.pre_mirror_snapshot:
        return Path(args.pre_mirror_snapshot).resolve()
    if args.repo_root:
        return default_pre_mirror_snapshot_path(Path(args.repo_root).resolve())
    return default_pre_mirror_snapshot_path(Path.cwd().resolve())


def _cmd_plan(args: argparse.Namespace) -> int:
    snap = _resolve_snapshot_path(args)
    old = load_schemas_from_snapshot(snap)
    new = load_current_table_schemas(
        Path(args.repo_root).resolve() if args.repo_root else None,
        tables_dir=Path(args.tables_dir).resolve() if args.tables_dir else None,
    )
    try:
        if getattr(args, "against_database", False):
            db = DatabaseManager()
            db.initialize()
            try:
                diff, plan = build_migration_plan(
                    old,
                    new,
                    database_type=db.config.get("database_type", args.database_type),
                    db=db,
                )
            finally:
                db.close()
        else:
            diff, plan = build_migration_plan(old, new, database_type=args.database_type)
    except MigrationPlanError as e:
        logger.error("%s", e)
        return 2

    steps = ordered_plan(plan)
    if args.json:
        payload = {
            "snapshot": str(snap),
            "tables_changed": len(diff.non_unchanged()),
            "step_count": len(steps),
            "warnings": plan.warnings,
            "steps": [
                {
                    "step_id": s.step_id,
                    "kind": s.kind.value,
                    "action_id": s.action_id,
                    "depends_on": list(s.depends_on),
                    "sql": s.sql,
                }
                for s in steps
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"snapshot: {snap}")
        print(f"tables with changes: {len(diff.non_unchanged())}")
        print(f"steps: {len(steps)}")
        for w in plan.warnings:
            print(f"warning: {w}")
        for s in steps:
            print(f"\n--- {s.step_id} [{s.kind.value}] action_id={s.action_id} ---")
            print(s.sql)
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    snap = _resolve_snapshot_path(args)
    if not snap.is_file():
        logger.error("schema 快照不存在: %s", snap)
        return 1
    try:
        result = run_schema_migration(
            pre_mirror_snapshot=snap,
            repo_root=Path(args.repo_root).resolve() if args.repo_root else None,
            tables_dir=Path(args.tables_dir).resolve() if args.tables_dir else None,
            apply=not args.dry_run,
            against_database=args.dry_run,
            database_type=args.database_type,
        )
    except MigrationPlanError as e:
        logger.error("无法生成迁移计划: %s", e)
        return 2
    except Exception as e:
        logger.exception("迁移失败: %s", e)
        return 3

    if result.skipped_reason:
        logger.info("跳过迁移: %s", result.skipped_reason)
        if getattr(args, "result_json", None):
            _write_migration_result_json(Path(args.result_json).resolve(), result)
        return 0

    logger.info(
        "old=%s new=%s steps=%s applied=%s",
        result.old_schema_count,
        result.new_schema_count,
        result.step_count,
        result.applied,
    )
    for w in (result.plan.warnings if result.plan else []):
        logger.warning("%s", w)

    if args.dry_run:
        logger.info("dry-run：未执行 DDL")

    if getattr(args, "result_json", None):
        _write_migration_result_json(Path(args.result_json).resolve(), result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--repo-root", help="仓库根（定位 core/tables 与默认快照路径）")
    shared.add_argument(
        "--pre-mirror-snapshot",
        help="镜像前 schema 快照 JSON（默认 userspace/.ntq/update/cache/pre_mirror_core_table_schemas.json）",
    )
    shared.add_argument("--tables-dir", help="覆盖 core/tables 目录（测试用）")
    shared.add_argument(
        "--database-type",
        choices=("postgresql", "mysql"),
        default="postgresql",
        help="plan 阶段 SQL 方言（apply 时以 DatabaseManager 配置为准）",
    )

    p = argparse.ArgumentParser(description="NTQ core/tables schema 升级")
    p.add_argument("-v", "--verbose", action="store_true")

    sub = p.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", parents=[shared], help="仅 diff + plan，不连库执行")
    plan_p.add_argument("--json", action="store_true", help="以 JSON 输出 plan")
    plan_p.add_argument(
        "--against-database",
        action="store_true",
        help="连库 introspection 并裁剪已在库中的步骤（不执行 DDL）",
    )
    plan_p.set_defaults(func=_cmd_plan)

    apply_p = sub.add_parser("apply", parents=[shared], help="diff + plan + 执行 DDL")
    apply_p.add_argument("--dry-run", action="store_true", help="只生成 plan，不执行 DDL")
    apply_p.add_argument(
        "--result-json",
        help="将 MigrationRunResult 摘要写入 JSON（updater 子进程使用）",
    )
    apply_p.set_defaults(func=_cmd_apply)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
