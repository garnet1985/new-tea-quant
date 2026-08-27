"""module_info.yaml 为版本 SSOT：changelog / 文档头必须对齐。"""
from __future__ import annotations

from core.infra.cli.dev.scripts.publish_prep.publish_prep import (
    validate_module_doc_versions,
    validate_module_info_changelog,
)

import pytest

pytestmark = pytest.mark.force_run


def test_module_info_changelog_matches_version() -> None:
    issues = validate_module_info_changelog()
    assert issues == [], "\n".join(issues)


def test_module_docs_match_module_info_version() -> None:
    issues = validate_module_doc_versions()
    assert issues == [], "\n".join(issues)
