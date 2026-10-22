"""校验 PostProcessor 声明与所引用 adapter。"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from core.modules.post_process.core.adapter_validator import AdapterValidator
from core.modules.post_process.core.post_processor_loader import PostProcessorLoader
from core.modules.post_process.core.post_processor_types import PostProcessorDefinition


class PostProcessorValidator:
    @staticmethod
    def validate(key: str) -> Tuple[bool, str]:
        name = str(key or "").strip()
        if not name:
            return False, "post_processor key 不能为空"
        if PostProcessorLoader.resolve_path(name) is None:
            return False, f"未找到 post_processor 声明: {name}"
        definition = PostProcessorLoader.load(name)
        if definition is None:
            return False, f"无法解析 post_processor: {name}"
        return PostProcessorValidator.validate_definition(definition)

    @staticmethod
    def validate_definition(definition: PostProcessorDefinition) -> Tuple[bool, str]:
        if not definition.adapters:
            return False, f"post_processor '{definition.key}' 未声明任何 adapter"

        known = set(definition.adapters.keys())
        for aname, binding in definition.adapters.items():
            ok, err = AdapterValidator.validate(aname)
            if not ok:
                return False, f"adapter '{aname}': {err}"
            for dep in binding.depends_on:
                if dep not in known:
                    return (
                        False,
                        f"adapter '{aname}' depends_on '{dep}' "
                        f"不在本 post_processor 的 adapters 中",
                    )

        cycle = PostProcessorValidator._find_cycle(definition)
        if cycle:
            return False, f"depends_on 存在环: {' -> '.join(cycle)}"
        return True, ""

    @staticmethod
    def _find_cycle(definition: PostProcessorDefinition) -> List[str]:
        graph: Dict[str, List[str]] = {
            name: list(binding.depends_on)
            for name, binding in definition.adapters.items()
        }
        visiting: Set[str] = set()
        visited: Set[str] = set()
        stack: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            if node in visited:
                return None
            if node in visiting:
                if node in stack:
                    i = stack.index(node)
                    return stack[i:] + [node]
                return [node, node]
            visiting.add(node)
            stack.append(node)
            for dep in graph.get(node, []):
                hit = dfs(dep)
                if hit:
                    return hit
            stack.pop()
            visiting.remove(node)
            visited.add(node)
            return None

        for name in sorted(graph.keys()):
            hit = dfs(name)
            if hit:
                return hit
        return []


__all__ = ["PostProcessorValidator"]
