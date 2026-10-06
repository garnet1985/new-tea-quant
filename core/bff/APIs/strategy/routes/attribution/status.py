"""Attribution button readiness (A1-00)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.infra.project_context import ProjectContext
from core.modules.strategy import Strategy
from core.modules.strategy.contracts import WorkbenchStep
from core.modules.strategy.core.engines.analyzer.steps.campaign.config import (
    ATTRIBUTION_FILE_NAME,
    AttributionConfig,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.execute import (
    ExecuteStep,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.persist import (
    AttributionGroupStore,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.persist.base import (
    REPORT_FILE,
)
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator

logger = logging.getLogger(__name__)

EXAMPLE_PATH = "userspace/strategies/_template/empty_strategy/attribution.py"

_TOOLTIP_NEED_CONFIG = (
    "需要在策略目录配置 attribution.py 才能开始归因。"
    f"可参考模板：{EXAMPLE_PATH}"
)
_TOOLTIP_NEED_RUN = "请先完成本层回测。"
_TOOLTIP_INVALID = (
    "attribution.py 存在但无法用于参数归因"
    "（需要本层 inputs / versions）。"
    f"可参考模板：{EXAMPLE_PATH}"
)

_TASK_BY_STEP = {
    "enum": "enumerate",
    "price": "price_factor",
    "portfolio": "portfolio",
}


def _readiness_tooltip(has_primary: bool, config_ok: bool, config_reason: str) -> str:
    """按钮禁用时说明还缺什么。未跑本层时也要提到 attribution 配置。"""
    if has_primary and config_ok:
        return ""
    if config_ok:
        return _TOOLTIP_NEED_RUN
    config_text = (
        _TOOLTIP_INVALID if config_reason == "invalid" else _TOOLTIP_NEED_CONFIG
    )
    if has_primary:
        return config_text
    return f"{_TOOLTIP_NEED_RUN}{config_text}"


class AttributeStatus:
    """Probe visible / enabled for the attribution button on a workbench step.

    ``visible`` 仍表示本层主回测已完成（报告页签用）。
    按钮本身始终渲染，是否可点看 ``enabled``（本层已跑过且 attribution 配置有效）。
    """

    @classmethod
    def probe(cls, strategy_name: str, norm_step: str) -> Dict[str, Any]:
        name = str(strategy_name or "").strip()
        step = str(norm_step or "").strip()
        kind = WorkbenchStep.parse(step).to_simulate_kind()
        folder = Strategy.resolve_folder(name)

        has_primary, _vid = cls._has_primary(folder, name, kind)
        config_ok, config_reason = cls._config_ok(folder, kind.value)
        last_group_id = cls._last_group_id(folder, name, step) if has_primary else None

        visible = bool(has_primary)
        enabled = bool(visible and config_ok)
        if not has_primary:
            reason = "layer_not_run"
        elif not config_ok:
            reason = (
                "attribution_not_configured"
                if config_reason == "missing"
                else "attribution_invalid"
            )
        else:
            reason = "ok"
        tooltip = _readiness_tooltip(has_primary, config_ok, config_reason)

        return {
            "step": step,
            "visible": visible,
            "enabled": enabled,
            "reason": reason,
            "tooltip": tooltip,
            "example_path": EXAMPLE_PATH,
            "has_primary": has_primary,
            "config_ok": config_ok,
            "last_group_id": last_group_id,
        }

    @classmethod
    def _has_primary(
        cls, folder: Path, strategy_name: str, kind
    ) -> Tuple[bool, Optional[str]]:
        info = DiscoveryService.find_strategy(strategy_name)
        if info is None:
            return False, None
        try:
            fp = ExecuteStep.for_layer(kind)._baseline_fingerprints(info)
            vid = VersionMetaStore.find_version_by_fingerprints(
                ArtifactStore.simulations_root(folder),
                str(fp.execute_fp or ""),
                str(fp.env_fp or ""),
            )
            if not vid:
                return False, None
            if VersionMetaStore.step_status(
                ArtifactStore.simulations_root(folder), vid, kind
            ) != "ok":
                return False, None
            return True, str(vid)
        except Exception:
            logger.exception(
                "attribute status primary probe failed strategy=%s kind=%s",
                strategy_name,
                getattr(kind, "value", kind),
            )
            return False, None

    @classmethod
    def _config_ok(cls, folder: Path, layer: str) -> Tuple[bool, str]:
        path = Path(folder) / ATTRIBUTION_FILE_NAME
        if not path.is_file():
            return False, "missing"
        try:
            raw = path.read_text(encoding="utf-8").strip()
        except OSError:
            return False, "missing"
        if not raw:
            return False, "missing"
        try:
            cfg = AttributionConfig.load(folder, layer=layer)
            cfg.require_parameter()
        except FileNotFoundError:
            return False, "missing"
        except Exception:
            return False, "invalid"
        return True, "ok"

    @classmethod
    def _last_group_id(
        cls, folder: Path, strategy_name: str, norm_step: str
    ) -> Optional[str]:
        info = DiscoveryService.find_strategy(strategy_name)
        if info is None:
            return None
        env_fp = str(FingerprintCalculator.to_env_fingerprint(info) or "").strip()
        if not env_fp:
            return None
        root = ProjectContext.path.get_strategy_attribution_directory(folder)
        group_id = AttributionGroupStore.find(root, env_fp)
        if not group_id:
            return None
        task = _TASK_BY_STEP.get(norm_step)
        if not task:
            return None
        report_path = Path(root) / group_id / task / REPORT_FILE
        if not report_path.is_file():
            return None
        return group_id


__all__ = ["AttributeStatus", "EXAMPLE_PATH"]
