"""供应商发现单测：隔离 tmp 目录，不依赖本机 userspace。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context import ProjectContext
from core.modules.assistant.core.provider_catalog import ProviderCatalog


def _write_provider(
    providers_root: Path,
    provider_id: str,
    *,
    body: str,
    api_key: str | None = None,
) -> Path:
    directory = providers_root / provider_id
    directory.mkdir(parents=True)
    (directory / "config.py").write_text(body, encoding="utf-8")
    if api_key is not None:
        (directory / "api_key.txt").write_text(api_key, encoding="utf-8")
    return directory


def _patch_providers_root(monkeypatch: pytest.MonkeyPatch, providers_root: Path) -> None:
    monkeypatch.setattr(
        ProjectContext.path,
        "get_assistant_providers_directory",
        lambda: providers_root,
    )


def test_empty_when_root_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "does-not-exist"
    _patch_providers_root(monkeypatch, missing)
    assert ProviderCatalog.list_providers() == []
    assert ProviderCatalog.get_provider("zhipu") is None


def test_discovers_valid_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "providers"
    directory = _write_provider(
        root,
        "zhipu",
        body=(
            "PROVIDER = {\n"
            '    "base_url": "https://open.bigmodel.cn/api/paas/v4/",\n'
            '    "model": "glm-4-flash",\n'
            '    "enabled": True,\n'
            "}\n"
        ),
        api_key="not-a-real-key\n",
    )
    _patch_providers_root(monkeypatch, root)

    found = ProviderCatalog.list_providers()
    assert len(found) == 1
    item = found[0]
    assert item.provider_id == "zhipu"
    assert item.directory == directory
    assert item.base_url == "https://open.bigmodel.cn/api/paas/v4"
    assert item.model == "glm-4-flash"
    assert item.enabled is True
    assert item.has_api_key is True
    assert not hasattr(item, "api_key")
    assert ProviderCatalog.get_provider("zhipu") == item


def test_save_api_key_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "providers"
    directory = _write_provider(
        root,
        "zhipu",
        body=(
            "PROVIDER = {\n"
            '    "base_url": "https://open.bigmodel.cn/api/paas/v4",\n'
            '    "model": "glm-4-flash",\n'
            "}\n"
        ),
    )
    _patch_providers_root(monkeypatch, root)

    assert ProviderCatalog.get_provider("zhipu").has_api_key is False
    ProviderCatalog.save_api_key(directory, "  secret-key  ")
    item = ProviderCatalog.get_provider("zhipu")
    assert item is not None
    assert item.has_api_key is True
    assert ProviderCatalog.load_api_key(directory) == "secret-key"
    assert "secret-key" not in str(item)


def test_skips_incomplete_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "providers"
    _write_provider(
        root,
        "broken",
        body='PROVIDER = {"base_url": "https://example.invalid"}\n',
    )
    _patch_providers_root(monkeypatch, root)
    assert ProviderCatalog.list_providers() == []
    assert ProviderCatalog.get_provider("broken") is None


def test_keeps_disabled_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "providers"
    _write_provider(
        root,
        "offline",
        body=(
            "PROVIDER = {\n"
            '    "base_url": "https://example.invalid/v1",\n'
            '    "model": "dummy",\n'
            '    "enabled": False,\n'
            "}\n"
        ),
    )
    _patch_providers_root(monkeypatch, root)
    item = ProviderCatalog.get_provider("offline")
    assert item is not None
    assert item.enabled is False
    assert item.has_api_key is False


def test_paths_come_from_project_context() -> None:
    userspace = ProjectContext.path.get_userspace_root()
    expected_root = userspace / "extensions" / "assistant"
    expected_providers = expected_root / "providers"
    assert ProjectContext.path.get_assistant_root() == expected_root
    assert ProjectContext.path.get_assistant_providers_directory() == expected_providers
    assert (
        ProjectContext.path.get_assistant_provider_directory("zhipu")
        == expected_providers / "zhipu"
    )
