#!/usr/bin/env python3
"""
安装流程中的一步：可选导入 Demo 数据。

由仓库根目录 install.py 按顺序调用。

规则（无需环境变量开关）：
- 若 userspace/demo_data 不存在：跳过（打印原因）
- 若目录存在但没有任何 .zip：跳过（打印原因）
- 若检测到 zip：
  - 交互终端：展示导入计划并等待用户输入 YES，确认后执行导入，否则跳过
  - 非交互终端：跳过（打印原因，并提示手动命令）
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from setup.setup import NewTeaQuantSetup

def main() -> int:
    # 注意：本步骤要先做“纯文件检查”，避免在依赖未安装时 import installer 触发 DB 驱动导入失败。
    data_dir = _REPO_ROOT / "userspace" / "demo_data"
    if not data_dir.is_dir():
        NewTeaQuantSetup.print_check_ok(f"未发现 Demo 数据目录，跳过导入: {data_dir}")
        return 0

    zips = sorted(data_dir.glob("*.zip"))
    if not zips:
        NewTeaQuantSetup.print_check_ok(f"Demo 数据目录下未找到 .zip，跳过导入: {data_dir}")
        return 0

    NewTeaQuantSetup.print_check_ok(f"发现 Demo 数据包: {len(zips)} 个 zip（目录: {data_dir}）")

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not interactive:
        NewTeaQuantSetup.print_check_ok(
            f"非交互终端，跳过 Demo 数据导入。可手动执行: {sys.executable} -m setup.import_demo_data.cli --confirm"
        )
        return 0

    NewTeaQuantSetup.print_check_info("将展示导入计划；输入大写 YES 才会开始导入。")
    try:
        from setup.import_demo_data.installer import DemoDataInstaller
    except ModuleNotFoundError as e:
        # 典型场景：依赖未安装（例如 psycopg2/pymysql），先引导用户跑 resolve_deps
        NewTeaQuantSetup.print_check_fail(f"无法开始 Demo 导入（缺少依赖）: {e}")
        NewTeaQuantSetup.print_check_ok("请先运行安装步骤 resolve_deps，确保数据库驱动已安装。")
        return 1

    # 不加前缀：直接写入原表名（会覆盖同名表数据）
    inst = DemoDataInstaller(data_dir=data_dir, table_prefix="")
    try:
        inst.run(confirmed=False, confirm_nonempty=False, remove_extract=True)
    except SystemExit as e:
        # 用户未输入 YES 等情况，installer 会 exit；这里视为“跳过”或“失败”按其 code 透传
        code = int(getattr(e, "code", 1) or 1)
        if code == 1:
            NewTeaQuantSetup.print_check_ok("已取消 Demo 导入（未确认）。")
            return 0
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
