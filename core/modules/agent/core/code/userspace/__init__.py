"""Userspace agent 扩展：tools（代码）/ templates·prompts（md）。"""

from core.modules.agent.core.code.userspace.prompts import (
    append_userspace_prompt,
    load_userspace_prompt_snippet,
)
from core.modules.agent.core.code.userspace.templates import (
    list_userspace_template_matches,
    load_merged_template,
    match_userspace_scenario,
    merged_scenario_keys,
    userspace_template_path,
)
from core.modules.agent.core.code.userspace.tools import (
    get_userspace_tool_handler,
    list_userspace_tool_specs,
)

__all__ = [
    "append_userspace_prompt",
    "get_userspace_tool_handler",
    "list_userspace_template_matches",
    "list_userspace_tool_specs",
    "load_merged_template",
    "load_userspace_prompt_snippet",
    "match_userspace_scenario",
    "merged_scenario_keys",
    "userspace_template_path",
]
