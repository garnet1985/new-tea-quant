"""生产默认地址常量。

运行时一律用 ``site_target.base_url()``（及由其派生的函数）。
这里的常量只表示未改配置时的远端默认值。
"""

from .site_target import (
    DEFAULT_BASE_URL,
    ai_base_url,
    base_url,
    contact_url,
    disclaimer_url,
    doc_url,
    feedback_url,
    license_url,
    member_profile_url,
    register_url,
    trace_url,
)

OFFICIAL_BASE_URL = DEFAULT_BASE_URL
MEMBER_PROFILE_URL = f"{OFFICIAL_BASE_URL}/api/v1/ntq-member/profile"
AI_BASE_URL = f"{OFFICIAL_BASE_URL}/api/v1/ntq-ai"
FEEDBACK_URL = f"{OFFICIAL_BASE_URL}/api/v1/feedback"
TRACE_URL = f"{OFFICIAL_BASE_URL}/api/v1/traces"
CONTACT_URL = f"{OFFICIAL_BASE_URL}/zh-hans/contact?from=ntq_app"
DISCLAIMER_URL = f"{OFFICIAL_BASE_URL}/zh-hans/disclaimer"
LICENSE_URL = f"{OFFICIAL_BASE_URL}/zh-hans/ntq-license"
REGISTER_URL = f"{OFFICIAL_BASE_URL}/zh-hans/user/register"
DOC_STRATEGY_URL = f"{OFFICIAL_BASE_URL}/zh-hans/using-strategy-example"
DOC_OPPORTUNITIES_URL = f"{OFFICIAL_BASE_URL}/zh-hans/using-strategy-to-find-opportunities"
DOC_TAG_URL = f"{OFFICIAL_BASE_URL}/zh-hans/using-tag-example"
DOC_DATASOURCE_URL = f"{OFFICIAL_BASE_URL}/zh-hans/using-datasource-example"
DOC_CONTRACT_URL = f"{OFFICIAL_BASE_URL}/zh-hans/using-data-contract-example"

__all__ = [
    "OFFICIAL_BASE_URL",
    "DEFAULT_BASE_URL",
    "MEMBER_PROFILE_URL",
    "AI_BASE_URL",
    "FEEDBACK_URL",
    "TRACE_URL",
    "CONTACT_URL",
    "DISCLAIMER_URL",
    "LICENSE_URL",
    "REGISTER_URL",
    "DOC_STRATEGY_URL",
    "DOC_OPPORTUNITIES_URL",
    "DOC_TAG_URL",
    "DOC_DATASOURCE_URL",
    "DOC_CONTRACT_URL",
    "base_url",
    "ai_base_url",
    "member_profile_url",
    "register_url",
    "feedback_url",
    "trace_url",
    "contact_url",
    "disclaimer_url",
    "license_url",
    "doc_url",
]
