from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.setup.core.env import NewTeaQuantSetup


def test_require_supported_venv_rejects_older_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(NewTeaQuantSetup, "interpreter_version", classmethod(lambda cls, python: (3, 9)))
    with pytest.raises(SystemExit, match="Python 3.9"):
        NewTeaQuantSetup.require_supported_venv(Path("venv/bin/python"))


def test_require_supported_venv_accepts_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(NewTeaQuantSetup, "interpreter_version", classmethod(lambda cls, python: (3, 11)))
    NewTeaQuantSetup.require_supported_venv(Path("venv/bin/python"))
