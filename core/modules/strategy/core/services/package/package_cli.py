"""策略交流包 CLI 入口（类方法；供 modules.cli 调用）。"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional, Union

from core.infra.export_import import ExportImport
from core.infra.project_context import ProjectContext

from .bundle import (
    export_strategy_bundle,
    import_strategy_bundle,
    preview_strategy_bundle_import,
)
from .filenames import bundle_filename, parse_export_target, single_entity_filename
from .single import export_single_entity

logger = logging.getLogger(__name__)


def _out(message: str) -> None:
    """命令结果。开发诊断仍走 logger。"""
    print(message, flush=True)


class PackageCli:
    """策略包导出 / 导入 CLI 编排。"""

    @staticmethod
    def default_export_dir() -> Path:
        """Prefer userspace/; fall back to project root when userspace is absent."""
        us = ProjectContext.path.get_userspace_root()
        if us.is_dir():
            return us
        return ProjectContext.path.get_project_root()

    @staticmethod
    def default_export_path(mode: str, name: str) -> Path:
        if mode == "bundle":
            filename = bundle_filename(name)
        else:
            filename = single_entity_filename(mode, name)
        return PackageCli.default_export_dir() / filename

    @staticmethod
    def resolve_import_policy(
        *, force: bool, skip_existing: bool
    ) -> ExportImport.types.ConflictPolicy:
        if force and skip_existing:
            raise ValueError("cannot combine -f with --skip-existing")
        if force:
            return ExportImport.types.ConflictPolicy.OVERWRITE
        if skip_existing:
            return ExportImport.types.ConflictPolicy.SKIP_EXISTING
        return ExportImport.types.ConflictPolicy.REJECT

    @staticmethod
    def run_export(
        target: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> int:
        """Dispatch bundle or single-entity export based on target syntax."""
        try:
            mode, name = parse_export_target(target)
        except ValueError as exc:
            _out(f"导出失败：{exc}")
            return 1

        if mode == "bundle":
            return PackageCli.run_strategy_bundle_export(name, output_path=output_path)
        return PackageCli.run_single_entity_export(mode, name, output_path=output_path)

    @staticmethod
    def run_strategy_bundle_export(
        strategy_name: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> int:
        """Export strategy share bundle (strategy + resolved dependencies)."""
        name = str(strategy_name or "").strip()
        if not name:
            _out("导出失败：请提供策略名称（例: cli.py ex example）")
            return 1

        out = (
            Path(output_path)
            if output_path
            else PackageCli.default_export_path("bundle", name)
        )
        try:
            manifest, payload = export_strategy_bundle(name, output_path=out)
        except FileNotFoundError as exc:
            _out(f"导出失败：{exc}")
            return 1
        except ValueError as exc:
            _out(f"导出失败：{exc}")
            return 1
        except Exception as exc:
            _out(f"导出失败：{exc}")
            logger.exception("导出失败")
            return 1

        PackageCli._finalize_export_output(out, manifest, payload)
        _out(f"策略包: {name}")
        return 0

    @staticmethod
    def run_single_entity_export(
        kind: str,
        name: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> int:
        """Export a single strategy, tag, or adapter directory."""
        out = (
            Path(output_path)
            if output_path
            else PackageCli.default_export_path(kind, name)
        )
        try:
            manifest, payload = export_single_entity(kind, name, output_path=out)
        except FileNotFoundError as exc:
            _out(f"导出失败：{exc}")
            return 1
        except ValueError as exc:
            _out(f"导出失败：{exc}")
            return 1
        except Exception as exc:
            _out(f"导出失败：{exc}")
            logger.exception("导出失败")
            return 1

        PackageCli._finalize_export_output(out, manifest, payload)
        _out(f"单实体: {kind}:{name}")
        return 0

    @staticmethod
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
            _out(f"导入失败：找不到包文件 {path}")
            return 1

        try:
            policy = PackageCli.resolve_import_policy(
                force=force, skip_existing=skip_existing
            )
        except ValueError as exc:
            _out(f"导入失败：{exc}")
            return 1

        try:
            blob = path.read_bytes()
            preview = preview_strategy_bundle_import(blob, policy=policy)
        except Exception as exc:
            _out(f"导入失败：无法读取或解析包 — {exc}")
            logger.exception("导入失败")
            return 1

        PackageCli._log_import_preview(preview)

        if dry_run:
            if preview.get("ok"):
                _out("预览完成（--dry-run，未写入磁盘）")
                return 0
            _out("预览失败：存在冲突（可用 -f 覆盖或 --skip-existing 跳过已有）")
            return 1

        if not preview.get("ok"):
            _out("导入失败：目标路径已存在（使用 -f 覆盖或 --skip-existing 跳过）")
            return 1

        try:
            result = import_strategy_bundle(blob, policy)
        except Exception as exc:
            _out(f"导入失败：{exc}")
            logger.exception("导入失败")
            return 1

        if not result.ok:
            for err in result.errors:
                _out(f"  {err}")
            return 1

        name = preview.get("strategy_name") or preview.get("entity_name") or "?"
        dest = ProjectContext.path.get_userspace_root().resolve()
        _out(f"导入完成: {name} → {dest}")
        if result.skipped:
            skipped = ", ".join(f"{e.kind}:{e.name}" for e in result.skipped)
            _out(f"已跳过（本机已存在）: {skipped}")
        return 0

    @staticmethod
    def _finalize_export_output(out: Path, manifest, payload) -> None:
        if not isinstance(payload, Path):
            out.write_bytes(bytes(payload))
        elif payload.resolve() != out.resolve():
            out.write_bytes(payload.read_bytes())
        PackageCli._clear_macos_xattrs(out)
        kinds = ", ".join(sorted({e.kind for e in manifest.entries}))
        _out(f"已导出: {out.resolve()}")
        _out(f"制品: {kinds} | 条目数: {len(manifest.entries)}")
        _out(
            "提示: 请用 cli.py im <文件> 或 unzip -l <文件> 查看/导入；"
            "勿在 Finder 里双击 zip（iCloud 桌面下 Archive Utility 易异常）。"
        )

    @staticmethod
    def _log_import_preview(preview: dict) -> None:
        strategy_name = preview.get("strategy_name") or preview.get("entity_name") or "?"
        bundle_type = preview.get("bundle_type") or "?"
        _out(
            f"包类型: {bundle_type} | 主实体: {preview.get('entity_name')} | 策略: {strategy_name}"
        )
        _out(f"冲突策略: {preview.get('policy')}")

        for row in preview.get("items") or []:
            status = row.get("status")
            label = f"{row.get('kind')} {row.get('name')}"
            if status == "will_install":
                _out(f"  将安装: {label}")
            elif status == "exists_skip":
                _out(f"  已存在，跳过: {label}")
            elif status == "conflict":
                _out(f"  冲突: {label} → userspace/{row.get('target_relative')}")

    @staticmethod
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


__all__ = ["PackageCli"]
