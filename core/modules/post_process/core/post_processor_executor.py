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


class PostProcessorExecutor:
    @staticmethod
    def run(key: str, session: ScanSessionReport) -> None:
        definition = PostProcessorLoader.load(key)
        if definition is None:
            raise ValueError(f"无法加载 post_processor: {key}")
        PostProcessorExecutor.run_definition(definition, session)

    @staticmethod
    def run_definition(
        definition: PostProcessorDefinition,
        session: ScanSessionReport,
    ) -> None:
        if not isinstance(session, ScanSessionReport):
            raise TypeError("session 须为 ScanSessionReport")

        opp_count = sum(len(s.opportunities) for s in session.strategies)
        if definition.on_empty == "skip" and opp_count == 0:
            logger.info(
                "[PostProcessor] %s on_empty=skip 且无机会，跳过",
                definition.key,
            )
            return

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


__all__ = ["PostProcessorExecutor"]
