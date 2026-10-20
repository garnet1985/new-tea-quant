"""给其他模块看的官网地址。运行时走 site_target。"""

from __future__ import annotations

from typing import Dict

from core.modules.ntq_external.conf.site_target import (
    contact_url,
    disclaimer_url,
    doc_url,
    license_url,
    register_url,
)


def site_urls() -> Dict[str, object]:
    """页面地址。调用方拿不到模块时当作没有官网。"""
    return {
        "disclaimer_url": disclaimer_url(),
        "license_url": license_url(),
        "contact_url": contact_url(),
        "register_url": register_url(),
        "docs": {
            "strategy": doc_url("using-strategy-example"),
            "opportunities": doc_url("using-strategy-to-find-opportunities"),
            "tag": doc_url("using-tag-example"),
            "datasource": doc_url("using-datasource-example"),
            "contract": doc_url("using-data-contract-example"),
        },
    }
