"""执行 PostProcessor：拓扑排序后逐个调用 adapter。"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.modules.post_process.core.adapter_loader import AdapterLoader
from core.modules.post_process.core.post_processor_loader import PostProcessorLoader
from core.modules.post_process.core.post_processor_types import PostProcessorDefinition
from core.modules.post_process.core.protocol import ScanSessionReport
from core.modules.post_process.core.topo import topological_order

logger = logging.getLogger(__name__)

# SPECIAL-CASE（见 docs/DECISIONS.md DEC-05）：仅 presenter 写入扫描页 UI 槽。
# 第二个会改前端渲染的 adapter 出现时，改为通用契约 + FED 解析引擎，废掉此硬编码。
_SCAN_UI_ADAPTER = "presenter"
_SCAN_UI_SLOT = "scan_report"
_SCAN_UI_VIEW = "presenter"


def ui_contributions_from_outputs(outputs: Dict[str, Any]) -> Dict[str, Any]:
    """从单次 PostProcessor 的 adapter outputs 抽出 scan UI 贡献（写死 presenter）。"""
    props = outputs.get(_SCAN_UI_ADAPTER) if isinstance(outputs, dict) else None
    if not isinstance(props, dict) or not props:
        return {}
    return {
        _SCAN_UI_SLOT: {
            "view": _SCAN_UI_VIEW,
            "props": props,
        }
    }


class PostProcessorExecutor:
    @staticmethod
    def run(key: str, session: ScanSessionReport) -> Dict[str, Any]:
        definition = PostProcessorLoader.load(key)
        if definition is None:
            raise ValueError(f"无法加载 post_processor: {key}")
        return PostProcessorExecutor.run_definition(definition, session)

    @staticmethod
    def run_definition(
        definition: PostProcessorDefinition,
        session: ScanSessionReport,
    ) -> Dict[str, Any]:
        if not isinstance(session, ScanSessionReport):
            raise TypeError("session 须为 ScanSessionReport")

        opp_count = sum(len(s.opportunities) for s in session.strategies)
        if definition.on_empty == "skip" and opp_count == 0:
            logger.info(
                "[PostProcessor] %s on_empty=skip 且无机会，跳过",
                definition.key,
            )
            return {}

        order = topological_order(definition)
        outputs: Dict[str, Any] = {}

        for name in order:
            binding = definition.adapters[name]
            cls = AdapterLoader.load_class(name)
            if cls is None:
                msg = f"adapter '{name}' 无法加载"
                if definition.on_error == "stop":
                    raise RuntimeError(msg)
                logger.error("[PostProcessor] %s: %s", definition.key, msg)
                continue

            default_cfg = AdapterLoader.load_default_config(name)
            config = {**default_cfg, **dict(binding.config or {})}
            deps = {dep: outputs[dep] for dep in binding.depends_on if dep in outputs}

            try:
                result = cls(adapter_name=name).run(session, config, deps)
                outputs[name] = result
            except Exception as exc:
                logger.error(
                    "[PostProcessor] %s adapter '%s' 失败: %s",
                    definition.key,
                    name,
                    exc,
                    exc_info=True,
                )
                if definition.on_error == "stop":
                    raise

        return outputs


__all__ = [
    "PostProcessorExecutor",
    "ui_contributions_from_outputs",
]
