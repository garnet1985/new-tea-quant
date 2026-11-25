"""PostProcessor adapter 拓扑排序（depends_on）。"""

from __future__ import annotations

from typing import Dict, List

from core.modules.post_process.core.post_processor_types import PostProcessorDefinition


def topological_order(definition: PostProcessorDefinition) -> List[str]:
    """返回可执行顺序：依赖在前。无依赖时按名称稳定排序。"""
    graph: Dict[str, List[str]] = {
        name: list(binding.depends_on)
        for name, binding in definition.adapters.items()
    }
    indegree: Dict[str, int] = {name: 0 for name in graph}
    children: Dict[str, List[str]] = {name: [] for name in graph}
    for name, deps in graph.items():
        for dep in deps:
            if dep not in graph:
                continue
            children[dep].append(name)
            indegree[name] = indegree.get(name, 0) + 1

    ready = sorted([n for n, d in indegree.items() if d == 0])
    ordered: List[str] = []
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        for child in sorted(children.get(node, [])):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()

    if len(ordered) != len(graph):
        raise ValueError(f"depends_on 无法拓扑排序（可能有环）: {definition.key}")
    return ordered


__all__ = ["topological_order"]
