"""技术指标模块（``modules.indicator``）。

公开门面::

    from core.modules.indicator import Indicator

类型::

    from core.modules.indicator.contracts import BatchIndicatorResult

字段命名::

    from core.modules.indicator import field_naming
"""

from core.modules.indicator.core import field_naming
from core.modules.indicator.core.indicator import Indicator

__all__ = ["Indicator", "field_naming"]
