"""PostProcess 模块（``modules.post_process``）。

公开门面::

    from core.modules.post_process import PostProcess

契约（协议 / BaseAdapter）::

    from core.modules.post_process.contracts import (
        BaseAdapter,
        Opportunity,
        StrategyScanReport,
        ScanSessionReport,
    )
"""

from .post_process import PostProcess

__all__ = ["PostProcess"]
