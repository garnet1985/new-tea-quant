"""
交互式应用升级入口（供 ``run_apply.py``、``start-cli -u`` 共用）。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import helper
from pipeline import UpgradeContext, check_remote_has_newer_version, run_upgrade_pipeline


def resolve_updater_dir(start: Optional[Path] = None) -> Path:
    """定位 ``userspace/updater`` 或开发时 ``setup/updater``。"""
    if start is not None:
        candidates = [start.resolve()]
    else:
        here = Path(__file__).resolve().parent
        candidates = [here]
    if not candidates[0].joinpath("pipeline.py").is_file():
        repo = candidates[0]
        for _ in range(6):
            for sub in (repo / "userspace" / "updater", repo / "setup" / "updater"):
                if (sub / "pipeline.py").is_file():
                    return sub.resolve()
            if repo.parent == repo:
                break
            repo = repo.parent
    if not candidates[0].joinpath("pipeline.py").is_file():
        raise FileNotFoundError("未找到 updater（userspace/updater 或 setup/updater）")
    return candidates[0]


def repo_root_from_updater(updater_dir: Path) -> Path:
    u = updater_dir.resolve()
    if u.name == "updater" and u.parent.name == "userspace":
        return u.parent.parent.resolve()
    if u.name == "updater" and u.parent.name == "setup":
        return u.parent.parent.resolve()
    return u.parent.resolve()


def _user_confirms_upgrade(newer_version: str) -> bool:
    try:
        ans = input(f"发现更新版本：{newer_version}，是否自动升级？").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes", "是", "好", "ok")


def run_interactive_upgrade(
    repo_root: Path,
    *,
    assume_yes: bool = False,
) -> int:
    """
    探测远端版本 → 已最新则提示并返回；有新版本则询问用户 → 确认后执行 ``run_upgrade_pipeline``。

    Returns:
        进程退出码（0 成功 / 取消 / 已最新；非 0 失败）。
    """
    repo_root = repo_root.resolve()
    local_ver = helper.read_local_version(repo_root)
    if not local_ver:
        print("无法读取本地版本（缺少 core/system.json 或 version 字段）", file=sys.stderr)
        return 1

    newer = check_remote_has_newer_version(repo_root)
    if newer is None:
        print(f"已经是最新版本了（{local_ver}）")
        return 0

    if not assume_yes and not _user_confirms_upgrade(newer):
        print("已取消升级。")
        return 0

    print("开始升级，请勿关闭终端…")
    ctx = UpgradeContext(repo_root=repo_root)
    try:
        run_upgrade_pipeline(ctx)
    except Exception as exc:
        print(f"升级失败: {exc}", file=sys.stderr)
        return 1

    print(f"升级完成。当前版本请查看 core/system.json（目标版本 {newer}）。")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="NTQ 应用升级（交互式）")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="仓库根目录（默认由 updater 路径推断）",
    )
    parser.add_argument("-y", "--yes", action="store_true", help="发现新版本时不询问，直接升级")
    args = parser.parse_args(argv)

    updater_dir = resolve_updater_dir()
    repo = args.repo_root.resolve() if args.repo_root else repo_root_from_updater(updater_dir)
    return run_interactive_upgrade(repo, assume_yes=args.yes)
