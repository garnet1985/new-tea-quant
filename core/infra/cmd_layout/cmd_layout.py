"""CmdLayout facade — public entry for CLI layout helpers."""

from .bar_chart.bar_chart import BarChartNamespace
from .icon.icon import IconNamespace
from .table.table import TableNamespace
from .text.text import TextNamespace
from .title.title import TitleNamespace


class CmdLayout:
    """CmdLayout module facade for CLI report rendering helpers."""

    bar_chart = BarChartNamespace
    title = TitleNamespace
    table = TableNamespace
    text = TextNamespace
    icon = IconNamespace


__all__ = ["CmdLayout"]
