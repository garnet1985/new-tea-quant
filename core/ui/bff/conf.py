import os

from core.ui.ports import BFF_DEFAULT_PORT, FED_DEV_PORT

conf = {
    "DEBUG": False,
    "PORT": BFF_DEFAULT_PORT,
    "HOST": "127.0.0.1",
    "CORS_ALLOW_ORIGINS": [
        f"http://localhost:{FED_DEV_PORT}",
        f"http://127.0.0.1:{FED_DEV_PORT}",
    ],
    "CORS_ALLOW_METHODS": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "CORS_ALLOW_HEADERS": ["Content-Type", "Authorization"],
    "CORS_ALLOW_CREDENTIALS": True,
    "CORS_MAX_AGE": 3600,
    "THREADED": os.environ.get("BFF_THREADED", "").lower() in ("1", "true", "yes"),
}
