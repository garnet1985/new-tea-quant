"""使用条款同意：只认当前修订，记录不进 userspace。"""

from __future__ import annotations

import json

import pytest

import core.infra.setup.core.license_acceptance as lic

pytestmark = pytest.mark.force_run

_REAL_APPLY = lic.apply_trace_consent


@pytest.fixture(autouse=True)
def _no_trace_side_effect(monkeypatch):
    monkeypatch.setattr(lic, "apply_trace_consent", lambda: None)


@pytest.fixture
def acceptance_file(tmp_path, monkeypatch):
    path = tmp_path / "license_acceptance.json"
    monkeypatch.setattr(lic, "acceptance_path", lambda: path)
    return path


def test_missing_file_is_not_accepted(acceptance_file):
    assert lic.is_accepted() is False
    assert lic.entry_path() == "/setup/license"


def test_current_revision_is_accepted(acceptance_file):
    acceptance_file.write_text(
        json.dumps({"revision": lic.LICENSE_REVISION}),
        encoding="utf-8",
    )
    assert lic.is_accepted() is True
    assert lic.entry_path() == "/strategy-design"


def test_old_revision_is_not_accepted(acceptance_file):
    acceptance_file.write_text(json.dumps({"revision": "0"}), encoding="utf-8")
    assert lic.is_accepted() is False


def test_y_and_capital_y_accept(acceptance_file, monkeypatch):
    monkeypatch.setattr(lic, "_stdin_is_tty", lambda: True)
    answers = iter(["n", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    assert lic.ensure_accepted(source="cli") is False
    assert acceptance_file.is_file() is False
    assert lic.ensure_accepted(source="cli") is True
    saved = json.loads(acceptance_file.read_text(encoding="utf-8"))
    assert saved["revision"] == lic.LICENSE_REVISION
    assert saved["source"] == "cli"


def test_blank_and_other_text_reject(acceptance_file, monkeypatch):
    monkeypatch.setattr(lic, "_stdin_is_tty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "yes")
    assert lic.ensure_accepted(source="install") is False
    assert acceptance_file.exists() is False


def test_noninteractive_without_flag_rejects(acceptance_file, monkeypatch):
    monkeypatch.setattr(lic, "_stdin_is_tty", lambda: False)
    monkeypatch.delenv(lic._ACCEPT_ENV, raising=False)
    assert lic.ensure_accepted(source="install") is False
    assert acceptance_file.exists() is False


def test_flag_and_env_accept_without_prompt(acceptance_file, monkeypatch):
    monkeypatch.setattr(lic, "_stdin_is_tty", lambda: False)
    assert lic.ensure_accepted(source="install", assume_accepted=True) is True
    assert lic.is_accepted() is True

    acceptance_file.unlink()
    monkeypatch.setenv(lic._ACCEPT_ENV, "1")
    assert lic.ensure_accepted(source="install") is True
    assert json.loads(acceptance_file.read_text(encoding="utf-8"))["source"] == "install"


def test_already_accepted_does_not_prompt(acceptance_file, monkeypatch):
    lic.accept(source="ui")

    def _boom(_prompt=""):
        raise AssertionError("should not prompt")

    monkeypatch.setattr("builtins.input", _boom)
    assert lic.ensure_accepted(source="cli") is True


def test_apply_grants_only_after_userspace_and_license(acceptance_file, tmp_path, monkeypatch):
    userspace = tmp_path / "userspace"
    monkeypatch.setattr(
        "core.infra.project_context.core.path_manager.PathManager.get_userspace_root",
        lambda: userspace,
    )
    granted = []
    decided = {"value": False}

    monkeypatch.setattr(
        "core.infra.trace.core.services.consent_service.TraceConsentService.is_decided",
        lambda: decided["value"],
    )
    monkeypatch.setattr(
        "core.infra.trace.core.services.consent_service.TraceConsentService.grant",
        lambda *, source="": granted.append(source) or True,
    )

    _REAL_APPLY()
    assert granted == []

    acceptance_file.write_text(
        json.dumps({"revision": lic.LICENSE_REVISION}),
        encoding="utf-8",
    )
    _REAL_APPLY()
    assert granted == []

    marker = userspace / "system" / "config" / "database" / "common.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{}\n", encoding="utf-8")
    _REAL_APPLY()
    assert granted == ["license"]

    decided["value"] = True
    granted.clear()
    _REAL_APPLY()
    assert granted == []
