#!/usr/bin/env python3
"""开发用 CLI：导入 userspace/demo_data 下的 zip 到带前缀的表（默认 test_）。"""
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

from setup.demo_data_handler.installer import DemoDataInstaller

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="解压 userspace/demo_data 下所有 zip，按表导入到 {prefix}{表名}（默认不覆盖原表）"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="默认 userspace/demo_data",
    )
    parser.add_argument(
        "--prefix",
        default="test_",
        help="目标表前缀，默认 test_",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="已阅读上方打印的安装计划并确认执行；非交互/管道场景下必填",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="非交互时使用：目标表已有数据时仍执行；需与 --confirm 同用。交互式无需此参数（输入 YES 即可）",
    )
    parser.add_argument(
        "--keep-extract",
        action="store_true",
        help="成功后仍保留 _extract 解压目录",
    )
    args = parser.parse_args()

    inst = DemoDataInstaller(data_dir=args.data_dir, table_prefix=args.prefix)
    try:
        inst.run(
            confirmed=args.confirm,
            confirm_nonempty=args.yes,
            remove_extract=not args.keep_extract,
        )
    except SystemExit:
        raise
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

    logging.info("Demo 数据导入完成")


if __name__ == "__main__":
    main()
