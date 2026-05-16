"""生产模式：将 ``fed/build`` 挂到 BFF（SPA 回退；``/static/*`` 见 ``app.create_app``）。"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, abort, send_from_directory

_FED_BUILD_DIR = Path(__file__).resolve().parent.parent / "fed" / "build"


def resolve_fed_build_dir() -> Path:
    raw = (os.environ.get("NTQ_FED_BUILD_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _FED_BUILD_DIR.resolve()


def fed_build_static_dir(build_dir: Path | None = None) -> Path:
    return (build_dir or resolve_fed_build_dir()) / "static"


def fed_build_ready(build_dir: Path | None = None) -> bool:
    root = build_dir or resolve_fed_build_dir()
    return (root / "index.html").is_file()


def register_fed_static_routes(app: Flask, build_dir: Path | None = None) -> bool:
    root = (build_dir or resolve_fed_build_dir()).resolve()
    if not fed_build_ready(root):
        return False

    @app.route("/favicon.ico", methods=["GET", "HEAD"])
    def serve_fed_favicon():
        if (root / "favicon.ico").is_file():
            return send_from_directory(str(root), "favicon.ico")
        abort(404)

    @app.route("/asset-manifest.json", methods=["GET", "HEAD"])
    def serve_fed_manifest():
        if (root / "asset-manifest.json").is_file():
            return send_from_directory(str(root), "asset-manifest.json")
        abort(404)

    @app.route("/", defaults={"path": ""}, methods=["GET", "HEAD"])
    @app.route("/<path:path>", methods=["GET", "HEAD"])
    def serve_fed_spa(path: str):
        if path.startswith("api/") or path == "api":
            abort(404)
        if path:
            candidate = root / path
            if candidate.is_file():
                return send_from_directory(str(candidate.parent), candidate.name)
        return send_from_directory(str(root), "index.html")

    print(f"FED build 已挂载: {root}", flush=True)
    return True
