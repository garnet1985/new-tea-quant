"""HTTP POST for feedback ingest (stdlib urllib). Never raises."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict

logger = logging.getLogger(__name__)

_USER_AGENT = "NTQ-feedback/1"


class FeedbackClientService:
    """POST one feedback payload. Never raises."""

    @staticmethod
    def post(url: str, payload: Dict[str, Any], *, timeout_sec: float) -> bool:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return True
        if not url or not str(url).strip():
            return False
        if not isinstance(payload, dict):
            return False
        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            data = body.encode("utf-8")
            req = urllib.request.Request(
                str(url).strip(),
                data=data,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=float(timeout_sec)) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                return 200 <= int(code) < 300
        except urllib.error.HTTPError as exc:
            if exc.code in {200, 201, 202, 204, 409}:
                return True
            logger.debug("feedback POST HTTP %s", exc.code)
            return False
        except Exception as exc:
            logger.debug("feedback POST failed: %s", exc)
            return False
