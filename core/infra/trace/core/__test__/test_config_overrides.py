"""TraceConfigService userspace / env override behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.infra.trace.core.defaults import TraceDefaults
from core.infra.trace.core.services.config_service import TraceConfigService

pytestmark = pytest.mark.force_run


def test_userspace_trace_json_overrides_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "trace.json").write_text(
        json.dumps({"target_url": "https://from-file.example/traces", "timeout_sec": 4.5}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.core.path_manager.PathManager.get_user_config_root",
        lambda: cfg_dir,
    )
    monkeypatch.delenv("NTQ_TRACE_ENDPOINT", raising=False)
    monkeypatch.delenv("NTQ_TRACE_TIMEOUT", raising=False)

    cfg = TraceConfigService.load()
    assert cfg.target_url == "https://from-file.example/traces"
    assert cfg.timeout_sec == 4.5


def test_env_beats_userspace_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "trace.json").write_text(
        json.dumps({"target_url": "https://from-file.example/traces"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.core.path_manager.PathManager.get_user_config_root",
        lambda: cfg_dir,
    )
    monkeypatch.setenv("NTQ_TRACE_ENDPOINT", "https://from-env.example/traces")

    cfg = TraceConfigService.load()
    assert cfg.target_url == "https://from-env.example/traces"


def test_defaults_single_source() -> None:
    assert TraceDefaults.TARGET_URL.startswith("https://")
    assert "target_url" in TraceDefaults.as_dict()
