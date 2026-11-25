"""编排层：交出工具清单，并执行已实现的工具。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.agent.contracts import ToolSpec
from core.modules.agent.core.code.pipeline import RunLoop
from core.modules.agent.core.code.conf.conf import (
    PREFERENCE_MAX_CHARS,
    PREFERENCE_MAX_RULES,
    SETTINGS_CONTEXT_PROMPT_LANE,
    USERSPACE_PROMPT_SNIPPET_MAX_CHARS,
)
from core.modules.agent.core.code.session.session_store import (
    clear_session,
    default_session_id,
    forget_preference,
    load_default_provider_id,
    load_preferences,
    recent_turns,
    remember_preference,
    replace_preferences,
    save_default_provider_id,
)
from core.modules.agent.core.code.userspace.prompts import (
    load_userspace_prompt_snippet,
    save_userspace_prompt_snippet,
)
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog
from core.modules.agent.core.code.tools.tool_runner import run_tool


class AgentManager:
    """内部编排。不对外导出。"""

    def __init__(self) -> None:
        self._catalog = ToolCatalog()

    def list_tools(self) -> List[ToolSpec]:
        return self._catalog.list_tools()

    def call_tool(
        self, name: str, arguments: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return run_tool(self._catalog, name, arguments)

    def run(
        self,
        content: str,
        *,
        session_id: Optional[str] = None,
        provider_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return RunLoop(self._catalog).run(
            content, session_id=session_id, provider_id=provider_id
        )

    def clear_session(self, session_id: Optional[str] = None) -> None:
        clear_session(session_id or default_session_id())

    def session_history(
        self, session_id: Optional[str] = None, *, limit: int = 20
    ) -> Dict[str, Any]:
        sid = session_id or default_session_id()
        return {
            "session_id": sid,
            "messages": recent_turns(sid, limit=max(1, int(limit))),
        }

    def list_preferences(self) -> List[str]:
        return load_preferences()

    def remember(self, rule: str) -> List[str]:
        return remember_preference(rule)

    def forget(self, rule: str) -> List[str]:
        return forget_preference(rule)

    def get_settings(self) -> Dict[str, Any]:
        lane = SETTINGS_CONTEXT_PROMPT_LANE
        return {
            "default_provider_id": load_default_provider_id(),
            "context_prompt": load_userspace_prompt_snippet(lane),
            "context_prompt_lane": lane,
            "context_prompt_max_chars": USERSPACE_PROMPT_SNIPPET_MAX_CHARS,
            "preferences": load_preferences(),
            "preference_max_rules": PREFERENCE_MAX_RULES,
            "preference_max_chars": PREFERENCE_MAX_CHARS,
        }

    def update_settings(
        self,
        *,
        default_provider_id: Optional[str] = None,
        context_prompt: Optional[str] = None,
        preferences: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if default_provider_id is not None:
            save_default_provider_id(default_provider_id)
        if context_prompt is not None:
            save_userspace_prompt_snippet(
                SETTINGS_CONTEXT_PROMPT_LANE, context_prompt
            )
        if preferences is not None:
            replace_preferences(preferences)
        return self.get_settings()
