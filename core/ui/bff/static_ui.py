"""
将 CRA 构建产物（``core/ui/fed/build``）挂到 BFF，供 ``launcher`` 生产模式使用。

API 仍走 ``/api/*`` 蓝图；其余路径回退到 ``index.html``（SPA）。
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, send_from_directory

_FED_BUILD_DIR = Path(__file__).resolve().parents[1] / "fed" / "build"


def resolve_fed_build_dir() -> Path:
    raw = (os.environ.get("NTQ_FED_BUILD_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _FED_BUILD_DIR.resolve()


def fed_build_ready(build_dir: Path | None = None) -> bool:
    root = build_dir or resolve_fed_build_dir()
    return (root / "index.html").is_file()


def register_fed_static_routes(app: Flask, build_dir: Path | None = None) -> bool:
    """
    注册静态资源与 SPA 回退路由。

    Returns:
        是否成功挂载（``index.html`` 存在）。
    """
    root = build_dir or resolve_fed_build_dir()
    if not fed_build_ready(root):
        return False

    @app.route("/", defaults={"path": ""}, methods=["GET", "HEAD"])
    @app.route("/<path:path>", methods=["GET", "HEAD"])
    def serve_fed_spa(path: str):
        if path.startswith("api/") or path == "api":
            return {"error": "not_found"}, 404
        if path:
            candidate = root / path
            if candidate.is_file():
                return send_from_directory(root, path)
        return send_from_directory(root, "index.html")

    return True
