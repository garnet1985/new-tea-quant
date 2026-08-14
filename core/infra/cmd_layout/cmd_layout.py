"""CmdLayout facade — public entry for CLI layout helpers."""

from .bar_chart.bar_chart import BarChartNamespace
from .icon.icon import IconNamespace
from .separator.separator import SeparatorNamespace
from .title.title import TitleNamespace


class CmdLayout:
    """CmdLayout module facade for CLI report rendering helpers."""

    bar_chart = BarChartNamespace
    title = TitleNamespace
    separator = SeparatorNamespace
    icon = IconNamespace


__all__ = ["CmdLayout"]
