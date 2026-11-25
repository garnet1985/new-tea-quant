"""Register series_relation route modules（先注册更具体的 /run /results）。"""

from . import runner_routes  # noqa: F401
from . import catalog_routes  # noqa: F401
