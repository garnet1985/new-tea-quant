import os

from core.ui.ports import UI_BFF_PORT, UI_DEV_PORT

_bff_port = int(os.getenv("NTQ_BFF_PORT", str(UI_BFF_PORT)))

conf = {
    "DEBUG": False,
    "PORT": _bff_port,
    "HOST": os.getenv("NTQ_BFF_HOST", "127.0.0.1").strip() or "127.0.0.1",
    "CORS_ALLOW_ORIGINS": [
        f"http://localhost:{UI_DEV_PORT}",
        f"http://127.0.0.1:{UI_DEV_PORT}",
        f"http://localhost:{UI_BFF_PORT}",
        f"http://127.0.0.1:{UI_BFF_PORT}",
    ],
    "CORS_ALLOW_METHODS": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "CORS_ALLOW_HEADERS": ["Content-Type", "Authorization"],
    "CORS_ALLOW_CREDENTIALS": True,
    "CORS_MAX_AGE": 3600,
    "THREADED": os.environ.get("BFF_THREADED", "1").lower() not in ("0", "false", "no"),
}
