"""CLI helpers for strategy share bundle export / import."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional, Union

from core.infra.export_import import ConflictPolicy
from core.infra.project_context import PathManager
from core.modules.strategy.services.package import (
    export_strategy_bundle,
    import_strategy_bundle,
    preview_strategy_bundle_import,
)

logger = logging.getLogger(__name__)

# Plain ``.zip`` suffix for macOS Finder / Archive Utility compatibility.
DEFAULT_BUNDLE_SUFFIX = ".strategy.zip"


def default_export_path(strategy_name: str) -> Path:
    safe = str(strategy_name or "").strip().replace("/", "_").replace("\\", "_")
    return Path.cwd() / f"{safe}{DEFAULT_BUNDLE_SUFFIX}"


def run_strategy_bundle_export(strategy_name: str, output_path: Optional[Union[str, Path]] = None) -> int:
    """Export strategy share bundle to a zip file. Returns process exit code."""
    name = str(strategy_name or "").strip()
    if not name:
        logger.error("导出失败：请提供策略名称（例: start-cli.py -e example）")
        return 1

    out = Path(output_path) if output_path else default_export_path(name)
    try:
        manifest, payload = export_strategy_bundle(name, output_path=out)
    except FileNotFoundError as exc:
        logger.error("导出失败：%s", exc)
        return 1
    except ValueError as exc:
        logger.error("导出失败：%s", exc)
        return 1
    except Exception as exc:
        logger.error("导出失败：%s", exc)
        return 1

    if not isinstance(payload, Path):
        out.write_bytes(bytes(payload))
    elif payload.resolve() != out.resolve():
        out.write_bytes(payload.read_bytes())

    _clear_macos_xattrs(out)

    kinds = ", ".join(sorted({e.kind for e in manifest.entries}))
    logger.info("已导出策略包: %s", out.resolve())
    logger.info("策略: %s | 制品: %s | 条目数: %d", name, kinds, len(manifest.entries))
    logger.info(
        "提示: 请用终端 ``unzip -l <文件>`` 或 ``start-cli.py -i <文件>``；"
        "不要在 Finder / Cursor 里点击打开该 zip（macOS 可能卡住）。"
    )
    return 0


def _clear_macos_xattrs(path: Path) -> None:
    """Remove Finder metadata xattrs that can confuse Archive Utility on local zips."""
    try:
        subprocess.run(
            ["xattr", "-c", str(path)],
            check=False,
            capture_output=True,
        )
    except Exception:
        pass


def run_strategy_bundle_import(package_path: Union[str, Path], *, force: bool = False) -> int:
    """Import strategy share bundle. Returns process exit code."""
    path = Path(package_path)
    if not path.is_file():
        logger.error("导入失败：找不到包文件 %s", path)
        return 1

    policy = ConflictPolicy.OVERWRITE if force else ConflictPolicy.REJECT
    try:
        blob = path.read_bytes()
        preview = preview_strategy_bundle_import(blob, policy=policy)
    except Exception as exc:
        logger.error("导入失败：无法读取或解析包 — %s", exc)
        return 1

    strategy_name = preview.get("strategy_name") or "?"
    if not preview.get("ok"):
        logger.error("导入失败：目标路径已存在（使用 -f 覆盖）")
        for row in preview.get("conflicts") or []:
            logger.error(
                "  冲突: %s %s → userspace/%s",
                row.get("kind"),
                row.get("name"),
                row.get("target_relative"),
            )
        return 1

    for row in preview.get("items") or []:
        status = row.get("status")
        if status == "will_install":
            logger.info("将安装: %s %s", row.get("kind"), row.get("name"))
        elif status == "exists_skip":
            logger.info("已存在，跳过: %s %s", row.get("kind"), row.get("name"))

    try:
        result = import_strategy_bundle(blob, policy)
    except Exception as exc:
        logger.error("导入失败：%s", exc)
        return 1

    if not result.ok:
        for err in result.errors:
            logger.error("  %s", err)
        return 1

    logger.info("策略包导入完成: %s → %s", strategy_name, PathManager.userspace().resolve())
    if result.skipped:
        skipped = ", ".join(f"{e.kind}:{e.name}" for e in result.skipped)
        logger.info("已跳过（本机已存在）: %s", skipped)
    return 0
