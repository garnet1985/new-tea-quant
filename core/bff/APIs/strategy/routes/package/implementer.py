"""Package implementer: call strategy core package services + ExportImport.

HTTP / multipart stay in routes (+ helpers); this layer owns export/import logic.

Export 路径参数约定为 ``meta.key``（短唯一 id）；同时兼容 strategy name
（userspace 相对 path，即 ``StrategyInfo.id()``）。核心 package API 仍吃 path name。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.modules.strategy import Strategy


class StrategyPackageImplementer:
    def __init__(self) -> None:
        self._pkg = None
        self._ConflictPolicy = None

    def lazy_load(self) -> "StrategyPackageImplementer":
        if self._pkg is None:
            from core.infra.export_import import ExportImport
            from core.modules.strategy.core.services import package as pkg

            self._pkg = pkg
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
        return Strategy.resolve(key_or_name)

    def export_zip(self, strategy_key_or_name: str, scope: str) -> Tuple[bytes, str]:
        """Return ``(zip_bytes, download_filename)``.

        ``strategy_key_or_name``: ``settings.meta.key`` 或 path name。
        """
        assert self._pkg is not None
        name = Strategy.resolve(strategy_key_or_name)
        scope_norm = str(scope or "bundle").strip().lower() or "bundle"

        if scope_norm == "bundle":
            _manifest, payload = self._pkg.export_strategy_bundle(name)
            filename = self._pkg.bundle_filename(name)
        elif scope_norm == "strategy":
            _manifest, payload = self._pkg.export_single_entity("strategy", name)
            filename = self._pkg.single_entity_filename("strategy", name)
        else:
            raise ValueError(f"无效 scope={scope_norm!r}；可选 bundle | strategy")

        if isinstance(payload, (bytes, bytearray)):
            data = bytes(payload)
        elif isinstance(payload, Path):
            data = payload.read_bytes()
        else:
            data = payload.read_bytes()
        return data, filename

    def preview_import(self, blob: bytes, policy: Any) -> Dict[str, Any]:
        assert self._pkg is not None
        return self._pkg.preview_strategy_bundle_import(blob, policy=policy)

    def import_bundle(
        self, blob: bytes, policy: Any
    ) -> Tuple[Dict[str, Any], Any]:
        """Run preview then import. Returns ``(preview, import_result)``."""
        assert self._pkg is not None
        preview = self._pkg.preview_strategy_bundle_import(blob, policy=policy)
        if not preview.get("ok"):
            return preview, None
        result = self._pkg.import_strategy_bundle(blob, policy)
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
