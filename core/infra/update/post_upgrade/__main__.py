"""升级收尾动作（post-upgrade）：``python -m core.infra.update.post_upgrade run``。"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from core.infra.update.post_upgrade.runner import PostUpgradeRunResult, run_post_upgrade_actions

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _write_result_json(path: Path, result: PostUpgradeRunResult) -> None:
    payload = {
        "skipped": result.skipped,
        "skipped_reason": result.skipped_reason,
        "action_ids": result.action_ids,
        "executed_count": result.executed_count,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _cmd_run(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    try:
        result = run_post_upgrade_actions(repo)
    except Exception:
        logger.exception("post-upgrade 执行失败")
        return 1

    if result.skipped_reason:
        logger.info("post-upgrade 跳过: %s", result.skipped_reason)
    else:
        logger.info(
            "post-upgrade 完成: executed=%s actions=%s",
            result.executed_count,
            result.action_ids,
        )

    if args.result_json:
        _write_result_json(Path(args.result_json).resolve(), result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--repo-root", default=".", help="仓库根目录")
    shared.add_argument("--result-json", help="写入执行摘要 JSON（updater 子进程使用）")

    p = argparse.ArgumentParser(description="NTQ 升级收尾（post-upgrade）动作")
    p.add_argument("-v", "--verbose", action="store_true")

    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", parents=[shared], help="执行已注册的收尾动作（无注册则跳过）")
    run_p.set_defaults(func=_cmd_run)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
