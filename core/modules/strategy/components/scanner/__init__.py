#!/usr/bin/env python3
"""Legacy scanner component bridges during migration."""

from .adapter_dispatcher import AdapterDispatcher
from .scan_cache_manager import ScanCacheManager
from .scan_date_resolver import ScanDateResolver

__all__ = [
    "AdapterDispatcher",
    "ScanCacheManager",
    "ScanDateResolver",
]

