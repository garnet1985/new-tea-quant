"""Lazy stack for strategy package export / import (userspace bundles)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

_stack: Optional[SimpleNamespace] = None


def get_strategy_package_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack

    from core.infra.export_import import ExportImport
    from core.modules.strategy.launcher.package_cli import (
        bundle_filename,
        parse_export_target,
        single_entity_filename,
    )
    from core.modules.strategy.services.package import (
        export_single_entity,
        export_strategy_bundle,
        import_strategy_bundle,
        preview_strategy_bundle_import,
    )

    _stack = SimpleNamespace(
        ConflictPolicy=ExportImport.types.ConflictPolicy,
        bundle_filename=bundle_filename,
        single_entity_filename=single_entity_filename,
        parse_export_target=parse_export_target,
        export_strategy_bundle=export_strategy_bundle,
        export_single_entity=export_single_entity,
        preview_strategy_bundle_import=preview_strategy_bundle_import,
        import_strategy_bundle=import_strategy_bundle,
    )
    return _stack
