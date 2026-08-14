"""Register tag route modules onto ``tag_api_bp``."""

from .catalog import routes as catalog_routes  # noqa: F401
from .runner import routes as runner_routes  # noqa: F401
