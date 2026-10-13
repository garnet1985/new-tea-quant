"""给其他模块看的官网地址。地址本身只在 conf。"""

from __future__ import annotations

from typing import Dict

from core.modules.ntq_external.conf.endpoints import (
    CONTACT_URL,
    DISCLAIMER_URL,
    DOC_CONTRACT_URL,
    DOC_DATASOURCE_URL,
    DOC_OPPORTUNITIES_URL,
    DOC_STRATEGY_URL,
    DOC_TAG_URL,
    LICENSE_URL,
    REGISTER_URL,
)


def site_urls() -> Dict[str, object]:
    """页面地址。调用方拿不到模块时当作没有官网。"""
    return {
        "disclaimer_url": DISCLAIMER_URL,
        "license_url": LICENSE_URL,
        "contact_url": CONTACT_URL,
        "register_url": REGISTER_URL,
        "docs": {
            "strategy": DOC_STRATEGY_URL,
            "opportunities": DOC_OPPORTUNITIES_URL,
            "tag": DOC_TAG_URL,
            "datasource": DOC_DATASOURCE_URL,
            "contract": DOC_CONTRACT_URL,
        },
    }
