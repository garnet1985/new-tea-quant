"""Provider：本地可见的唯一出入口选择。

- ``ntq``：会员凭证 → Website（模型调度与计费在远端）
- 其它 id：用户自备供应商，一个 Provider 干到底

见 ``docs/PROVIDER_AND_NAVIGATOR.md``。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from core.modules.agent.core.code.conf.conf import (
    DEV_OWN_DEFAULT_PROVIDER_ID,
    OWN_KEYS_ENV,
    PRODUCT_PROVIDER_ID,
)


@dataclass(frozen=True)
class Provider:
    """一次 Agent.run 锁定的 Provider。"""

    id: str
    available: bool
    unavailable_reason: str = ""

    @property
    def is_ntq(self) -> bool:
        return self.id == PRODUCT_PROVIDER_ID


def resolve_provider(provider_id: Optional[str] = None) -> Provider:
    """解析用户选定的 Provider；一个 id 全程使用。"""
    explicit = str(provider_id or "").strip()
    if explicit and explicit != PRODUCT_PROVIDER_ID:
        if not _local_key_ready(explicit):
            return Provider(
                id=explicit,
                available=False,
                unavailable_reason=f"供应商 {explicit} 未配置可用的 API Key。",
            )
        return Provider(id=explicit, available=True)

    if _dev_own_keys_enabled():
        pid = DEV_OWN_DEFAULT_PROVIDER_ID
        if not _local_key_ready(pid):
            return Provider(
                id=pid,
                available=False,
                unavailable_reason=(
                    f"NTQ_AGENT_OWN_KEYS 已开启，但默认供应商 {pid} 无 API Key。"
                ),
            )
        return Provider(id=pid, available=True)

    if not _membership_ready():
        return Provider(
            id=PRODUCT_PROVIDER_ID,
            available=False,
            unavailable_reason="NTQ AI 不可用：未装载会员凭证。",
        )
    return Provider(id=PRODUCT_PROVIDER_ID, available=True)


def _membership_ready() -> bool:
    try:
        from core.infra.membership import Membership

        return bool(str(Membership.read() or "").strip())
    except Exception:
        return False


def _local_key_ready(provider_id: str) -> bool:
    pid = str(provider_id or "").strip()
    if not pid or pid == PRODUCT_PROVIDER_ID:
        return False
    try:
        from core.infra.ai import AiChannel

        info = AiChannel.get_provider(pid)
        return bool(info and info.enabled and info.has_api_key)
    except Exception:
        return False


def _dev_own_keys_enabled() -> bool:
    return os.environ.get(OWN_KEYS_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
