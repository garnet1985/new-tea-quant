"""Package implementer: Strategy Facade + ExportImport policy。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.modules.strategy import Strategy


class StrategyPackageImplementer:
    def __init__(self) -> None:
        self._ConflictPolicy = None

    def lazy_load(self) -> "StrategyPackageImplementer":
        if self._ConflictPolicy is None:
            from core.infra.export_import import ExportImport

            self._ConflictPolicy = ExportImport.types.ConflictPolicy
        return self

    def resolve_policy(self, raw: Optional[str]) -> Any:
        assert self._ConflictPolicy is not None
        text = str(raw or "reject").strip().lower() or "reject"
        mapping = {
            "reject": self._ConflictPolicy.REJECT,
            "skip_existing": self._ConflictPolicy.SKIP_EXISTING,
            "overwrite": self._ConflictPolicy.OVERWRITE,
        }
        if text not in mapping:
            raise ValueError(
                f"无效 policy={text!r}；可选 reject | skip_existing | overwrite"
            )
        return mapping[text]

    @staticmethod
    def resolve_strategy_name(key_or_name: str) -> str:
        """``meta.key`` 或 path name → userspace 相对 path（package API 入参）。"""
        return Strategy.resolve_path(key_or_name)

    def export_zip(self, strategy_key_or_name: str, scope: str) -> Tuple[bytes, str]:
        """Return ``(zip_bytes, download_filename)``."""
        return Strategy.export_package_zip(strategy_key_or_name, scope=scope)

    def preview_import(self, blob: bytes, policy: Any) -> Dict[str, Any]:
        return Strategy.preview_package_import(blob, policy)

    def import_bundle(
        self, blob: bytes, policy: Any
    ) -> Tuple[Dict[str, Any], Any]:
        """Run preview then import. Returns ``(preview, import_result)``."""
        preview = Strategy.preview_package_import(blob, policy)
        if not preview.get("ok"):
            return preview, None
        result = Strategy.import_package_blob(blob, policy)
        return preview, result

    @staticmethod
    def import_ok_message(preview: Dict[str, Any], result: Any) -> Dict[str, Any]:
        return {
            "strategy_name": preview.get("strategy_name") or preview.get("entity_name"),
            "bundle_type": preview.get("bundle_type"),
            "policy": preview.get("policy"),
            "installed": [
                {"kind": e.kind, "name": e.name, "target_relative": e.target_relative}
                for e in result.installed
            ],
            "skipped": [
                {"kind": e.kind, "name": e.name, "target_relative": e.target_relative}
                for e in result.skipped
            ],
        }


impl = StrategyPackageImplementer()
