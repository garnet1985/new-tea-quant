"""post-upgrade 收尾动作执行器。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.infra.update.post_upgrade.registry import (
    clear_post_upgrade_registry,
    register_post_upgrade_action,
)
from core.infra.update.post_upgrade.runner import run_post_upgrade_actions


def test_run_skips_when_registry_empty():
    clear_post_upgrade_registry()
    with tempfile.TemporaryDirectory() as td:
        result = run_post_upgrade_actions(Path(td))
    assert result.skipped is True
    assert result.executed_count == 0


def test_run_executes_registered_actions_in_order():
    clear_post_upgrade_registry()
    seen: list[str] = []

    @register_post_upgrade_action("a_first")
    def _a(repo_root: Path, context: dict) -> None:
        seen.append("a")

    @register_post_upgrade_action("b_second")
    def _b(repo_root: Path, context: dict) -> None:
        seen.append("b")

    with tempfile.TemporaryDirectory() as td:
        result = run_post_upgrade_actions(Path(td), context={"k": 1})

    assert result.skipped is False
    assert result.executed_count == 2
    assert result.action_ids == ["a_first", "b_second"]
    assert seen == ["a", "b"]

    clear_post_upgrade_registry()
