"""
将 CRA 构建产物（``core/ui/fed/build``）挂到 BFF，供 ``launcher`` 生产模式使用。

API 仍走 ``/api/*`` 蓝图；``/static/*`` 与 SPA 回退单独注册（避免与 Flask 默认 static 冲突）。
"""
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


def fed_build_ready(build_dir: Path | None = None) -> bool:
    root = build_dir or resolve_fed_build_dir()
    return (root / "index.html").is_file()


def _safe_send(root: Path, rel: str):
    """从 build 根目录发送相对路径文件（防目录穿越）。"""
    rel = rel.lstrip("/").replace("\\", "/")
    if not rel or rel.startswith("..") or "/.." in rel:
        abort(404)
    directory = root
    filename = rel
    if "/" in rel:
        parent, filename = rel.rsplit("/", 1)
        directory = root / parent
    if not (directory / filename).is_file():
        abort(404)
    return send_from_directory(str(directory.resolve()), filename)


def register_fed_static_routes(app: Flask, build_dir: Path | None = None) -> bool:
    """
    注册静态资源与 SPA 回退路由。

    Returns:
        是否成功挂载（``index.html`` 存在）。
    """
    root = (build_dir or resolve_fed_build_dir()).resolve()
    if not fed_build_ready(root):
        return False

    static_root = root / "static"

    @app.route("/static/<path:asset_path>", methods=["GET", "HEAD"])
    def serve_fed_static(asset_path: str):
        if not static_root.is_dir():
            abort(404)
        return send_from_directory(str(static_root.resolve()), asset_path)

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
        if path.startswith("static/") or path in ("favicon.ico", "asset-manifest.json"):
            abort(404)
        if path:
            candidate = root / path
            if candidate.is_file():
                return _safe_send(root, path)
        return send_from_directory(str(root), "index.html")

    print(f"FED 静态资源已挂载: {root}", flush=True)
    return True
