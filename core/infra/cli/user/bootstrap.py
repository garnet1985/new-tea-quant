"""CLI bootstrap: venv re-exec and install gate."""

from __future__ import annotations

import os
import sys

from core.infra.cli.user.abbrev import expand_argv
from core.infra.cli.user.commands import EARLY_COMMANDS


def ensure_venv_for_cli(entry_file: str) -> None:
    """Re-exec into project venv when not already inside one."""
    raw = os.environ.get("NTQ_SKIP_AUTO_VENV", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return
    if sys.prefix != sys.base_prefix:
        return

    repo_root = os.path.dirname(os.path.abspath(entry_file))
    if os.name == "nt":
        vpy = os.path.join(repo_root, "venv", "Scripts", "python.exe")
    else:
        vpy = os.path.join(repo_root, "venv", "bin", "python")

    if os.path.isfile(vpy):
        os.execv(vpy, [vpy, os.path.abspath(entry_file), *sys.argv[1:]])


def should_skip_auto_install(argv: list[str]) -> bool:
    """Skip install.py when command does not need full runtime."""
    raw = os.environ.get("NTQ_SKIP_AUTO_INSTALL", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True

    if not argv:
        return True

    if argv[0] in ("-v", "--version"):
        return True

    if argv[0] in ("-h", "--help", "help"):
        return True

    if "-n" in argv or "--new" in argv:
        return True

    expanded = expand_argv(argv)
    return bool(expanded) and expanded[0] in EARLY_COMMANDS


def ensure_app_installed_if_needed() -> None:
    if should_skip_auto_install(sys.argv[1:]):
        return

    try:
        from setup.install_runtime import cli_install_scope, needs_install
    except ModuleNotFoundError:
        return

    if not needs_install("cli"):
        return

    scope = cli_install_scope()
    if scope == "deps_only":
        print("检测到 requirements.txt 变更，正在更新依赖 …", flush=True)
    else:
        print("检测到应用尚未完成安装，正在运行 install.py …", flush=True)
    from setup.cli_runtime import ensure_cli_install_via_install_py

    code = ensure_cli_install_via_install_py()
    if code != 0:
        raise SystemExit(code)
