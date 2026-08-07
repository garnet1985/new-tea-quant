"""ExportImport 门面（Facade）— infra.export_import 对外统一入口类。

实现位于 ``core/``；跨模块契约类型见 ``contracts.py``。
亦可经 ``ExportImport.types`` 取类型（与 contracts 同源）。
"""

from __future__ import annotations

from .contracts import (
    ArtifactSpec,
    BundleManifest,
    CollectedFile,
    ConflictItem,
    ConflictPolicy,
    InstallResult,
    ManifestEntry,
    PreflightResult,
)
from .core.namespaces import ArchiveNamespace, InstallNamespace


class TypesNamespace:
    """与 ``contracts`` 同源的类型挂载点。"""

    ArtifactSpec = ArtifactSpec
    BundleManifest = BundleManifest
    CollectedFile = CollectedFile
    ConflictItem = ConflictItem
    ConflictPolicy = ConflictPolicy
    InstallResult = InstallResult
    ManifestEntry = ManifestEntry
    PreflightResult = PreflightResult


class ExportImport:
    """New Tea Quant（NTQ）制品导出/导入门面类（Facade）。"""

    archive = ArchiveNamespace
    install = InstallNamespace
    types = TypesNamespace


__all__ = ["ExportImport"]
