#!/usr/bin/env python3
from __future__ import annotations

from setup.setup import NewTeaQuantSetup
from setup.ui_runtime import (
    check_runtime_prerequisites,
    install_ui_runtime,
    launch_ui_stack,
    needs_install,
)


def main() -> int:
    NewTeaQuantSetup.to_root_dir()
    NewTeaQuantSetup.ensure_venv()

    ok, msg = check_runtime_prerequisites()
    if not ok:
        print(f"❌ 运行环境检查失败: {msg}", flush=True)
        return 1

    required = needs_install()
    if required:
        print("检测到需要初始化安装，开始安装最小 UI 依赖...", flush=True)
        try:
            install_ui_runtime(force=True)
        except Exception as e:
            print(f"❌ 安装失败: {e}", flush=True)
            return 1
    else:
        print("安装状态已就绪。", flush=True)

    try:
        launch_ui_stack()
    except Exception as e:
        print(f"❌ UI 启动失败: {e}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
