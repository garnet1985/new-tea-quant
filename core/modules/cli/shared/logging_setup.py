"""Console logging for cli / devcli.

命令结果用 print。这里只配置开发诊断：默认警告及以上，--verbose 才输出 DEBUG。
"""

from __future__ import annotations

import logging


def setup_cli_logging(*, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
