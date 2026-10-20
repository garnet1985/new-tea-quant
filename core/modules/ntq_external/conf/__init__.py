"""对外通信配置。"""

from .endpoints import (
    AI_BASE_URL,
    CONTACT_URL,
    DISCLAIMER_URL,
    DOC_CONTRACT_URL,
    DOC_DATASOURCE_URL,
    DOC_OPPORTUNITIES_URL,
    DOC_STRATEGY_URL,
    DOC_TAG_URL,
    FEEDBACK_URL,
    LICENSE_URL,
    REGISTER_URL,
    TRACE_URL,
)
from .site_target import (
    DEFAULT_BASE_URL,
    ai_base_url,
    base_url,
)

__all__ = [
    "AI_BASE_URL",
    "CONTACT_URL",
    "DISCLAIMER_URL",
    "DOC_CONTRACT_URL",
    "DOC_DATASOURCE_URL",
    "DOC_OPPORTUNITIES_URL",
    "DOC_STRATEGY_URL",
    "DOC_TAG_URL",
    "FEEDBACK_URL",
    "LICENSE_URL",
    "REGISTER_URL",
    "TRACE_URL",
    "DEFAULT_BASE_URL",
    "base_url",
    "ai_base_url",
]
