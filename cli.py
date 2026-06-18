#!/usr/bin/env python3
# NTQ 用户 CLI。与 python cli.py -h 相同；维护请改 core/infra/cli/help_text.py
#
# 规则: xx=命令  -f/-n=全局  --xx=对象参数
#
# python cli.py sp -f --strategy xxx     同 strategy_price_factor
# python cli.py ex example               导出策略包
# python cli.py -n my_strategy           从模版新建策略到 my_strategy
#
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.infra.cli.bootstrap import ensure_app_installed_if_needed, ensure_venv_for_cli

ensure_venv_for_cli(__file__)
ensure_app_installed_if_needed()

try:
    from core.infra.cli.main import main
except ModuleNotFoundError as exc:
    missing = getattr(exc, "name", None) or str(exc)
    sys.stderr.write(
        "\n".join(
            [
                f"❌ 缺少依赖包: {missing}",
                "",
                "建议：在仓库根目录先执行一次安装（会创建 venv/ 并安装 requirements.txt）：",
                "  python3 install.py",
                "  或：python3 cli.py c  （将自动尝试 install.py）",
                "",
                "如果你已手动管理虚拟环境，请激活对应 venv 后再运行：",
                "  pip install -r requirements.txt",
                "",
                "如需跳过自动 venv（不推荐），可设置：NTQ_SKIP_AUTO_VENV=1",
                "",
            ]
        )
        + "\n"
    )
    raise SystemExit(1) from exc


if __name__ == "__main__":
    raise SystemExit(main())
