#!/usr/bin/env python3
"""开发用 CLI：导入 setup/init_data 下的 zip 到目标表（默认无前缀）。"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

from setup.setup_data.installer import SetupDataInstaller

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="导入 setup/init_data 下的初始化数据 zip"
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="默认 setup/init_data")
    parser.add_argument("--prefix", default="", help="目标表前缀，默认空")
    parser.add_argument("--force", action="store_true", help="忽略进度清单并全量重导")
    parser.add_argument("--keep-extract", action="store_true", help="成功后保留 _extract 目录")
    args = parser.parse_args()

    inst = SetupDataInstaller(data_dir=args.data_dir, table_prefix=args.prefix)
    try:
        inst.run(force=args.force, remove_extract=not args.keep_extract)
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        sys.exit(130)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    logging.info("初始化数据导入完成")


if __name__ == "__main__":
    main()
