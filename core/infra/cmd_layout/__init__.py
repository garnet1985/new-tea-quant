"""CmdLayout — CLI layout helpers for strategy report presentation.

See api.yaml for contract; title / separator / bar_chart / icon for ASCII layouts.
"""

from .cmd_layout import CmdLayout
from .icon import IconService, i

__all__ = ["CmdLayout", "IconService", "i"]
