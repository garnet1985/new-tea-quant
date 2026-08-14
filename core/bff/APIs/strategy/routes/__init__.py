"""Register strategy route modules onto ``strategy_api_bp``."""

from .catalog import routes as catalog_routes  # noqa: F401
from .package import routes as package_routes  # noqa: F401
from .report import routes as report_routes  # noqa: F401
from .runner import routes as runner_routes  # noqa: F401
from .settings import routes as settings_routes  # noqa: F401
from .version import routes as version_routes  # noqa: F401
