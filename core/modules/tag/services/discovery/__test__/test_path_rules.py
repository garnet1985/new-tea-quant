from core.modules.tag.services.discovery.path_rules import filesystem_safe_tag_key


def test_filesystem_safe_tag_key_replaces_slashes():
    assert filesystem_safe_tag_key("demo/market_cap_tier") == "demo_market_cap_tier"


def test_filesystem_safe_tag_key_fallback():
    assert filesystem_safe_tag_key("") == "unknown"
