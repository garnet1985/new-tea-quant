"""CmdLayout facade — public entry for CLI layout helpers."""

from .bar_chart import BarChartNamespace
from .separator import SeparatorNamespace
from .title import TitleNamespace


class CmdLayout:
    """CmdLayout module facade for CLI report rendering helpers."""

    bar_chart = BarChartNamespace()
    title = TitleNamespace()
    separator = SeparatorNamespace()


__all__ = ["CmdLayout"]
