#!/usr/bin/env python3
"""
写入 userspace/config/database/ 下的连接信息（与 ConfigManager 合并规则兼容）。

- 默认：交互式询问 PostgreSQL 或 MySQL；
- --from-examples：若目标 .json 不存在则从 .example.json 复制（不覆盖已有文件）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_DIR = _REPO_ROOT / "userspace" / "config" / "database"


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def copy_from_examples() -> int:
    """将 *.example.json 复制为 *.json（仅当目标不存在）。"""
    if not CONFIG_DIR.is_dir():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    examples = sorted(CONFIG_DIR.glob("*.example.json"))
    if not examples:
        print(f"未找到 {CONFIG_DIR}/*.example.json", file=sys.stderr)
        return 1
    n = 0
    for ex in examples:
        if not ex.name.endswith(".example.json"):
            continue
        target_name = ex.name.replace(".example.json", ".json")
        target = CONFIG_DIR / target_name
        if target.exists():
            print(f"已存在，跳过: {target}")
            continue
        shutil.copy2(ex, target)
        print(f"已创建: {target}（从 {ex.name}）")
        n += 1
    if n == 0:
        print("没有新文件可创建（目标均已存在）。如需覆盖请手动编辑。")
    return 0


def configure_interactive() -> int:
    try:
        import getpass
    except ImportError:
        getpass = None  # type: ignore

    print("请选择数据库类型：1=PostgreSQL  2=MySQL")
    choice = input("> ").strip()
    if choice == "1":
        db_type = "postgresql"
        default_port = 5432
    elif choice == "2":
        db_type = "mysql"
        default_port = 3306
    else:
        print("无效选择，已取消。", file=sys.stderr)
        return 1

    def _ask(label: str, default: str) -> str:
        s = input(f"{label} [{default}]: ").strip()
        return s if s else default

    host = _ask("主机", "localhost")
    port_s = _ask("端口", str(default_port))
    try:
        port = int(port_s)
    except ValueError:
        print("端口无效", file=sys.stderr)
        return 1
    database = _ask("数据库名", "stocks_py")
    user = _ask("用户名", "postgres" if db_type == "postgresql" else "root")
    if getpass:
        pw = getpass.getpass("密码: ")
    else:
        pw = input("密码: ").strip()

    common = {"database_type": db_type}
    conn = {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": pw,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(CONFIG_DIR / "common.json", common)
    _write_json(CONFIG_DIR / f"{db_type}.json", conn)

    print(f"已写入:\n  {CONFIG_DIR / 'common.json'}\n  {CONFIG_DIR / f'{db_type}.json'}")
    print("提示：敏感信息请勿提交到 Git；可改用环境变量覆盖（见 userspace/config/README.md）。")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="数据库配置写入 userspace/config/database/")
    parser.add_argument(
        "--from-examples",
        action="store_true",
        help="从 *.example.json 复制为 *.json（不覆盖已有文件）",
    )
    args = parser.parse_args()

    if args.from_examples:
        raise SystemExit(copy_from_examples())

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(
            "非交互终端。请使用:\n"
            "  python3 setup/db_init/db_install.py --from-examples\n"
            "或手动编辑 userspace/config/database/（见 userspace/config/README.md）",
            file=sys.stderr,
        )
        raise SystemExit(2)

    raise SystemExit(configure_interactive())


if __name__ == "__main__":
    main()
