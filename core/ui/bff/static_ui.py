"""
将 CRA 构建产物（``core/ui/fed/build``）挂到 BFF，供 ``launcher`` 生产模式使用。

``/static/*`` 由 Flask ``static_folder``（见 ``app.create_app``）提供；
本模块只注册 SPA 回退与其它根级资源。
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


def fed_build_static_dir(build_dir: Path | None = None) -> Path:
    return (build_dir or resolve_fed_build_dir()) / "static"


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
    注册 SPA 回退与根级静态文件（``/static/*`` 由 Flask ``static_folder`` 处理）。

    Returns:
        是否成功挂载（``index.html`` 存在）。
    """
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
                return _safe_send(root, path)
        return send_from_directory(str(root), "index.html")

    static_dir = fed_build_static_dir(root)
    print(
        f"FED 静态资源已挂载: build={root} static_url=/static -> {static_dir}",
        flush=True,
    )
    return True
