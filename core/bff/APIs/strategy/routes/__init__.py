"""Register strategy route modules onto ``strategy_api_bp``."""

from .catalog import routes as catalog_routes  # noqa: F401
from .package import routes as package_routes  # noqa: F401
from .report import routes as report_routes  # noqa: F401
from .version import routes as version_routes  # noqa: F401
