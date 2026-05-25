#!/usr/bin/env python3
"""
开发常用命令（仓库根目录，短选项与 ``start-cli.py`` 风格一致）。

  python dev-cli.py -ui     # 先清 8000/8888，再 launcher.py -d
  python dev-cli.py -kui    # 结束占用 8000 / 8888 的监听进程
  python dev-cli.py -ic     # UI 最小依赖 import 冒烟
  python dev-cli.py -cc     # 清空 userspace/.ntq（不动仓库根 .ntq / 安装状态）
  python dev-cli.py -cu     # 清空 userspace：各策略 results/ + DB 工作台快照
  python dev-cli.py -p -v0.3.2   # 发布前：写版本/徽章 + module_info + -ic + pytest
  python dev-cli.py -ex          # 打包演示数据（分层抽样 → setup/import_data 可导入 zip）

也支持子命令：``ui``、``kill``、``import-check``（见 ``-h``）。
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.ui.ports import BFF_DEFAULT_PORT, FED_DEV_PORT

UI_PORTS = (FED_DEV_PORT, BFF_DEFAULT_PORT)

# 短选项 → (handler_key, extra_kwargs)
_SHORT_FLAGS: dict[str, tuple[str, dict]] = {
    "-ui": ("ui", {"kill_first": True}),
    "-kui": ("kill", {"ntq_only": False}),
    "-ic": ("import-check", {}),
    "-cc": ("clear-global", {}),
    "-cu": ("clear-userspace", {}),
    "-ex": ("export-init-data", {}),
}


def _pids_listening_on(port: int) -> list[int]:
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("需要 lsof（macOS / Linux）", file=sys.stderr)
        return []
    return [int(line) for line in out.stdout.splitlines() if line.strip().isdigit()]


def _process_cmdline(pid: int) -> str:
    try:
        out = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    return (out.stdout or "").strip()


def kill_listeners_on_ports(
    ports: Iterable[int],
    *,
    ntq_only: bool = False,
) -> int:
    fed_root = str((REPO_ROOT / "core" / "ui" / "fed").resolve())
    repo_s = str(REPO_ROOT)
    ntq_markers = (
        "core.ui.bff.app",
        "react-scripts",
        "webpack",
        "launcher.py",
        "dev-cli.py",
        fed_root,
        repo_s,
    )
    killed = 0
    for port in ports:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            pids = _pids_listening_on(port)
            if not pids:
                break
            for pid in pids:
                cmd = _process_cmdline(pid)
                if ntq_only and cmd and not any(m in cmd for m in ntq_markers):
                    print(f"跳过 pid={pid}（非 NTQ UI）: {cmd[:120]}", flush=True)
                    continue
                print(f"结束 pid={pid}（:{port}） {cmd[:100]}", flush=True)
                try:
                    os.kill(pid, sig)
                    killed += 1
                except ProcessLookupError:
                    pass
            if not _pids_listening_on(port):
                break
            if sig == signal.SIGTERM:
                time.sleep(0.5)
    return killed


def _cmd_kill(args: argparse.Namespace) -> int:
    ports = tuple(args.port) if args.port else UI_PORTS
    n = kill_listeners_on_ports(ports, ntq_only=args.ntq_only)
    if n == 0:
        print(f"端口 {list(ports)} 上无监听进程。", flush=True)
    return 0


def _cmd_export_init_data(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "devtools.demo_exporter.demo_data_exporter", *args.forward]
    return subprocess.run(cmd, cwd=str(REPO_ROOT)).returncode


def _cmd_import_check(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "devtools.quick_tools.minimal_import_check", *args.forward]
    return subprocess.run(cmd, cwd=str(REPO_ROOT)).returncode


def _cmd_ui(args: argparse.Namespace) -> int:
    launcher = REPO_ROOT / "launcher.py"
    if not launcher.is_file():
        print(f"缺少 {launcher}", file=sys.stderr)
        return 1
    if args.kill_first:
        kill_listeners_on_ports(UI_PORTS, ntq_only=False)
    cmd = [sys.executable, str(launcher), "-d", *args.forward]
    print("启动: " + " ".join(cmd), flush=True)
    try:
        return subprocess.run(cmd, cwd=str(REPO_ROOT)).returncode
    except KeyboardInterrupt:
        return 130


def _cmd_clear_global(args: argparse.Namespace) -> int:
    from devtools.quick_tools.dev_cache import clear_userspace_ntq_dir

    clear_userspace_ntq_dir()
    print("userspace/.ntq 已清理。", flush=True)
    return 0


def _cmd_clear_userspace(args: argparse.Namespace) -> int:
    from devtools.quick_tools.dev_cache import clear_userspace_simulation_cache

    clear_userspace_simulation_cache()
    print("userspace 模拟缓存已清理。", flush=True)
    return 0


def _dispatch(handler: str, forward: list[str], extra: dict) -> int:
    ns = argparse.Namespace(
        forward=forward,
        port=None,
        ntq_only=extra.get("ntq_only", False),
        kill_first=extra.get("kill_first", False),
    )
    if handler == "ui":
        return _cmd_ui(ns)
    if handler == "kill":
        return _cmd_kill(ns)
    if handler == "import-check":
        return _cmd_import_check(ns)
    if handler == "export-init-data":
        return _cmd_export_init_data(ns)
    if handler == "clear-global":
        return _cmd_clear_global(ns)
    if handler == "clear-userspace":
        return _cmd_clear_userspace(ns)
    print(f"未知命令: {handler}", file=sys.stderr)
    return 2


def _normalize_forward(rest: Sequence[str]) -> list[str]:
    rest = list(rest)
    if rest[:1] == ["--"]:
        return rest[1:]
    return rest


def _print_help() -> None:
    print(
        """用法: python dev-cli.py <命令> [参数…]

短选项（推荐）:
  -ui      先 kill :8000/:8888，再 python launcher.py -d
  -kui     结束占用 8000、8888 的监听进程
  -ic      UI 最小依赖 import 检查
  -cc      删除 userspace/.ntq（不碰仓库根 .ntq / install-state）
  -cu      删除各策略 results/ 与 DB 工作台快照表
  -p -vX.Y.Z   发布准备（写 system.json / 徽章、检查 module_info、FED build、-ic、pytest）
  -ex         打包演示数据 zip（见 devtools/demo_exporter/demo_data_exporter.py）

  -p 附加: --check-only      只检查不写版本文件（仍会跑 FED build）
           --skip-tests       跳过 pytest
           --skip-ic          跳过最小依赖 import 检查
           --skip-fed-build   跳过 core/ui/fed 的 npm run build

子命令（等价）:
  ui [--kill-first]   kill [-ntq-only]   import-check   clear-cache   clear-userspace
  publish -v X.Y.Z    同 -p -vX.Y.Z
  export-init-data    同 -ex（参数用 -- 转发，如 -ex -- --to-init-data）

示例:
  python dev-cli.py -p -v0.3.2
  python dev-cli.py -ic -- --no-create-venv --python .ntq/ci-minimal-venv/bin/python
"""
    )


def _build_subcommand_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="New Tea Quant 开发命令")
    sub = parser.add_subparsers(dest="command")

    p_kill = sub.add_parser("kill", aliases=["k", "kill-ports"])
    p_kill.add_argument("--ntq-only", action="store_true")
    p_kill.add_argument("--port", type=int, action="append")
    p_kill.set_defaults(func=_cmd_kill, forward=[])

    p_check = sub.add_parser("import-check", aliases=["check-imports", "imports", "ic"])
    p_check.add_argument("forward", nargs=argparse.REMAINDER)
    p_check.set_defaults(func=_cmd_import_check)

    p_ui = sub.add_parser("ui", aliases=["dev", "launcher", "fed"])
    p_ui.add_argument("--kill-first", action="store_true")
    p_ui.add_argument("forward", nargs=argparse.REMAINDER)
    p_ui.set_defaults(func=_cmd_ui)

    p_cc = sub.add_parser(
        "clear-cache",
        aliases=["cc", "clear-global"],
        help="删除 userspace/.ntq（不含仓库根 .ntq）",
    )
    p_cc.set_defaults(func=_cmd_clear_global, forward=[])

    p_cu = sub.add_parser("clear-userspace", aliases=["cu", "clear-us"])
    p_cu.set_defaults(func=_cmd_clear_userspace, forward=[])

    p_ex = sub.add_parser(
        "export-init-data",
        aliases=["ex", "export-data", "export-demo"],
        help="打包演示数据为 setup/import_data 可导入 zip",
    )
    p_ex.add_argument("forward", nargs=argparse.REMAINDER)
    p_ex.set_defaults(func=_cmd_export_init_data)

    p_pub = sub.add_parser("publish", aliases=["p", "prep-release"])
    p_pub.add_argument("-v", "--version", required=True, help="目标版本 X.Y.Z 或 vX.Y.Z")
    p_pub.add_argument("--check-only", action="store_true")
    p_pub.add_argument("--skip-tests", action="store_true")
    p_pub.add_argument("--skip-ic", action="store_true")
    p_pub.add_argument("--skip-fed-build", action="store_true")
    p_pub.set_defaults(func=_cmd_publish, forward=[])

    return parser


def _cmd_publish(args: argparse.Namespace) -> int:
    from devtools.quick_tools.publish_prep import PublishPrepOptions, run_publish_prep

    return run_publish_prep(
        PublishPrepOptions(
            version=args.version,
            check_only=args.check_only,
            skip_tests=args.skip_tests,
            skip_ic=args.skip_ic,
            skip_fed_build=args.skip_fed_build,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(argv if argv is not None else sys.argv[1:])
    if not raw or raw[0] in ("-h", "--help", "help"):
        _print_help()
        return 0

    from devtools.quick_tools.publish_prep import parse_publish_argv, run_publish_prep

    pub, raw = parse_publish_argv(raw)
    if pub is not None:
        return run_publish_prep(pub)

    token = raw[0]
    rest = _normalize_forward(raw[1:])

    if token in _SHORT_FLAGS:
        handler, extra = _SHORT_FLAGS[token]
        return _dispatch(handler, rest, extra)

    parser = _build_subcommand_parser()
    args = parser.parse_args(raw)
    if not getattr(args, "command", None):
        _print_help()
        return 0
    forward = getattr(args, "forward", None) or []
    args.forward = _normalize_forward(forward)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
