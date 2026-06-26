"""CLI helpers for strategy share bundle export / import."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Union

from core.infra.project_context import ProjectContext
from core.infra.export_import import ConflictPolicy

from core.modules.strategy.services.package import (
    export_single_entity,
    export_strategy_bundle,
    import_strategy_bundle,
    preview_strategy_bundle_import,
)

logger = logging.getLogger(__name__)

BUNDLE_NAME_SUFFIX = "-strategy.zip"
_SINGLE_SUFFIX = {
    "strategy": "-strategy-only.zip",
    "tag": "-tag.zip",
    "adapter": "-adapter.zip",
}
_SINGLE_KINDS = frozenset(_SINGLE_SUFFIX)


def _sanitize_name(name: str) -> str:
    safe = str(name or "").strip()
    safe = safe.replace("/", "_").replace("\\", "_").replace(".", "-")
    return safe


def bundle_filename(strategy_name: str) -> str:
    return f"{_sanitize_name(strategy_name)}{BUNDLE_NAME_SUFFIX}"


def single_entity_filename(kind: str, name: str) -> str:
    k = str(kind or "").strip().lower()
    suffix = _SINGLE_SUFFIX.get(k)
    if not suffix:
        raise ValueError(f"unsupported single export kind: {kind!r}")
    return f"{_sanitize_name(name)}{suffix}"


def parse_export_target(raw: str) -> Tuple[str, str]:
    """
    Parse ``-e`` target.

    Returns ``("bundle", strategy_name)`` or ``(kind, name)`` for single export
    when ``kind`` is one of ``strategy``, ``tag``, ``adapter``.
    """
    text = str(raw or "").strip()
    if not text:
        raise ValueError("export target is required")
    if ":" not in text:
        return "bundle", text
    kind, name = text.split(":", 1)
    kind = kind.strip().lower()
    name = name.strip()
    if kind not in _SINGLE_KINDS:
        raise ValueError(
            f"unknown export kind {kind!r}; use tag:NAME, adapter:NAME, strategy:NAME, or bare strategy bundle name"
        )
    if not name:
        raise ValueError(f"export target {text!r} requires a name after ':'")
    return kind, name


def default_export_dir() -> Path:
    """Prefer userspace/; fall back to project root when userspace is absent."""
    us = ProjectContext.get_userspace_root()
    if us.is_dir():
        return us
    return PathManager.get_project_root()


def default_export_path(mode: str, name: str) -> Path:
    if mode == "bundle":
        filename = bundle_filename(name)
    else:
        filename = single_entity_filename(mode, name)
    return default_export_dir() / filename


def resolve_import_policy(*, force: bool, skip_existing: bool) -> ConflictPolicy:
    if force and skip_existing:
        raise ValueError("cannot combine -f with --skip-existing")
    if force:
        return ConflictPolicy.OVERWRITE
    if skip_existing:
        return ConflictPolicy.SKIP_EXISTING
    return ConflictPolicy.REJECT


def _finalize_export_output(out: Path, manifest, payload) -> None:
    if not isinstance(payload, Path):
        out.write_bytes(bytes(payload))
    elif payload.resolve() != out.resolve():
        out.write_bytes(payload.read_bytes())
    _clear_macos_xattrs(out)
    kinds = ", ".join(sorted({e.kind for e in manifest.entries}))
    logger.info("已导出: %s", out.resolve())
    logger.info("制品: %s | 条目数: %d", kinds, len(manifest.entries))
    logger.info(
        "提示: 请用 ``cli.py -i <文件>`` 或 ``unzip -l <文件>`` 查看/导入；"
        "勿在 Finder 里双击 zip（iCloud 桌面下 Archive Utility 易异常）。"
    )


def run_strategy_bundle_export(
    strategy_name: str,
    output_path: Optional[Union[str, Path]] = None,
) -> int:
    """Export strategy share bundle (strategy + resolved dependencies)."""
    name = str(strategy_name or "").strip()
    if not name:
        logger.error("导出失败：请提供策略名称（例: cli.py -e example）")
        return 1

    out = Path(output_path) if output_path else default_export_path("bundle", name)
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

    _finalize_export_output(out, manifest, payload)
    logger.info("策略包: %s", name)
    return 0


def run_single_entity_export(
    kind: str,
    name: str,
    output_path: Optional[Union[str, Path]] = None,
) -> int:
    """Export a single strategy, tag, or adapter directory."""
    out = Path(output_path) if output_path else default_export_path(kind, name)
    try:
        manifest, payload = export_single_entity(kind, name, output_path=out)
    except FileNotFoundError as exc:
        logger.error("导出失败：%s", exc)
        return 1
    except ValueError as exc:
        logger.error("导出失败：%s", exc)
        return 1
    except Exception as exc:
        logger.error("导出失败：%s", exc)
        return 1

    _finalize_export_output(out, manifest, payload)
    logger.info("单实体: %s:%s", kind, name)
    return 0


def run_export(
    target: str,
    output_path: Optional[Union[str, Path]] = None,
) -> int:
    """Dispatch bundle or single-entity export based on ``-e`` target syntax."""
    try:
        mode, name = parse_export_target(target)
    except ValueError as exc:
        logger.error("导出失败：%s", exc)
        return 1

    if mode == "bundle":
        return run_strategy_bundle_export(name, output_path=output_path)
    return run_single_entity_export(mode, name, output_path=output_path)


def _log_import_preview(preview: dict) -> None:
    strategy_name = preview.get("strategy_name") or preview.get("entity_name") or "?"
    bundle_type = preview.get("bundle_type") or "?"
    logger.info("包类型: %s | 主实体: %s | 策略: %s", bundle_type, preview.get("entity_name"), strategy_name)
    logger.info("冲突策略: %s", preview.get("policy"))

    for row in preview.get("items") or []:
        status = row.get("status")
        label = f"{row.get('kind')} {row.get('name')}"
        if status == "will_install":
            logger.info("  将安装: %s", label)
        elif status == "exists_skip":
            logger.info("  已存在，跳过: %s", label)
        elif status == "conflict":
            logger.error("  冲突: %s → userspace/%s", label, row.get("target_relative"))


def run_strategy_bundle_import(
    package_path: Union[str, Path],
    *,
    force: bool = False,
    skip_existing: bool = False,
    dry_run: bool = False,
) -> int:
    """Import a bundle archive. Returns process exit code."""
    path = Path(package_path)
    if not path.is_file():
        logger.error("导入失败：找不到包文件 %s", path)
        return 1

    try:
        policy = resolve_import_policy(force=force, skip_existing=skip_existing)
    except ValueError as exc:
        logger.error("导入失败：%s", exc)
        return 1

    try:
        blob = path.read_bytes()
        preview = preview_strategy_bundle_import(blob, policy=policy)
    except Exception as exc:
        logger.error("导入失败：无法读取或解析包 — %s", exc)
        return 1

    _log_import_preview(preview)

    if dry_run:
        if preview.get("ok"):
            logger.info("预览完成（--dry-run，未写入磁盘）")
            return 0
        logger.error("预览失败：存在冲突（可用 -f 覆盖或 --skip-existing 跳过已有）")
        return 1

    if not preview.get("ok"):
        logger.error("导入失败：目标路径已存在（使用 -f 覆盖或 --skip-existing 跳过）")
        return 1

    try:
        result = import_strategy_bundle(blob, policy)
    except Exception as exc:
        logger.error("导入失败：%s", exc)
        return 1

    if not result.ok:
        for err in result.errors:
            logger.error("  %s", err)
        return 1

    name = preview.get("strategy_name") or preview.get("entity_name") or "?"
    logger.info("导入完成: %s → %s", name, ProjectContext.get_userspace_root().resolve())
    if result.skipped:
        skipped = ", ".join(f"{e.kind}:{e.name}" for e in result.skipped)
        logger.info("已跳过（本机已存在）: %s", skipped)
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
