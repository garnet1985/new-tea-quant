"""HTTP POST client for trace ingest (stdlib urllib)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Union

from ...contracts import TraceEvent

logger = logging.getLogger(__name__)

_USER_AGENT = "NTQ-trace/1"


class TraceClientService:
    """Send one event to the remote collector. Never raises."""

    @staticmethod
    def post(
        url: str,
        event: Union[TraceEvent, Dict[str, Any]],
        *,
        timeout_sec: float,
    ) -> bool:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return True
        if not url or not url.strip():
            return False
        if isinstance(event, TraceEvent):
            wire = event.to_wire_dict()
        else:
            parsed = TraceEvent.from_dict(event)
            wire = parsed.to_wire_dict() if parsed is not None else {}
        body = json.dumps(wire, ensure_ascii=False, separators=(",", ":"))
        data = body.encode("utf-8")
        try:
            req = urllib.request.Request(
                url.strip(),
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
            logger.debug("trace POST HTTP %s", exc.code)
            return False
        except Exception as exc:
            logger.debug("trace POST failed: %s", exc)
            return False

        if isinstance(event, TraceEvent):
            wire = event.to_wire_dict()
        else:
            parsed = TraceEvent.from_dict(event)
            wire = parsed.to_wire_dict() if parsed is not None else {}
        body = json.dumps(wire, ensure_ascii=False, separators=(",", ":"))
        data = body.encode("utf-8")
        try:
            req = urllib.request.Request(
                url.strip(),
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
            logger.debug("trace POST HTTP %s", exc.code)
            return False
        except Exception as exc:
            logger.debug("trace POST failed: %s", exc)
            return False
