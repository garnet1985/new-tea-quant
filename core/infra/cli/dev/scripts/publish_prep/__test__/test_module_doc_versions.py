"""module_info.yaml 为版本 SSOT：changelog / name / 文档头必须对齐。"""
from __future__ import annotations

from pathlib import Path

from core.infra.cli.dev.scripts.publish_prep.module_versions import (
    expected_module_info_name,
    sync_module_doc_versions,
    validate_module_doc_versions,
    validate_module_info_changelog,
    validate_module_info_names,
)

import pytest

pytestmark = pytest.mark.force_run

_INFO = """\
name: {name}
version: "0.2.0"
compatible_core_versions: ">=0.4.5"
description: "t"
dependencies: []
changelog:
  - version: "{changelog_ver}"
    changes:
      - "init"
"""

_API = """\
# X API

**版本：** `{ver}`
**最低支持核心版本：** `{core}`

body
"""

_CASES = """\
# 测试用例

**覆盖版本：** `0.9.9`
"""


def test_module_info_changelog_matches_version() -> None:
    issues = validate_module_info_changelog()
    assert issues == [], "\n".join(issues)


def test_module_info_name_matches_path() -> None:
    issues = validate_module_info_names()
    assert issues == [], "\n".join(issues)


def test_module_docs_match_module_info_version() -> None:
    issues = validate_module_doc_versions()
    assert issues == [], "\n".join(issues)


def test_expected_module_info_name_singles() -> None:
    from core.infra.cli.dev.scripts.publish_prep import module_versions as mv

    repo = mv.REPO_ROOT
    assert expected_module_info_name(repo / "core" / "ui") == "ui"
    assert expected_module_info_name(repo / "core" / "bff") == "bff"
    assert expected_module_info_name(repo / "core" / "tables") == "tables"
    assert expected_module_info_name(repo / "core" / "infra" / "cli") == "infra.cli"
    assert expected_module_info_name(repo / "core" / "modules" / "strategy") == "modules.strategy"


def _write_mod(tmp: Path, *, name: str = "modules.demo", changelog_ver: str = "0.2.0") -> Path:
    root = tmp / "mod"
    root.mkdir()
    (root / "module_info.yaml").write_text(
        _INFO.format(name=name, changelog_ver=changelog_ver), encoding="utf-8"
    )
    (root / "API.md").write_text(_API.format(ver="0.2.0", core=">=0.4.5"), encoding="utf-8")
    cases = root / "__test__"
    cases.mkdir()
    (cases / "TEST_CASES.md").write_text(_CASES, encoding="utf-8")
    return root / "module_info.yaml"


def test_validate_rejects_legacy_cover_field(tmp_path: Path) -> None:
    info = _write_mod(tmp_path)
    issues = validate_module_doc_versions(info_paths=[info])
    assert any("非标准版本字段" in x for x in issues)
    assert any("TEST_CASES.md" in x for x in issues)


def test_validate_rejects_api_core_compat_drift(tmp_path: Path) -> None:
    info = _write_mod(tmp_path)
    api = info.parent / "API.md"
    api.write_text(_API.format(ver="0.2.0", core=">=0.4.4"), encoding="utf-8")
    (info.parent / "__test__" / "TEST_CASES.md").write_text(
        "**版本：** `0.2.0`\n", encoding="utf-8"
    )
    issues = validate_module_doc_versions(info_paths=[info])
    assert any("最低支持核心版本" in x for x in issues)


def test_sync_rewrites_cover_alias_and_number(tmp_path: Path) -> None:
    info = _write_mod(tmp_path)
    changed = sync_module_doc_versions(info_paths=[info])
    assert any(p.endswith("TEST_CASES.md") for p in changed)
    text = (info.parent / "__test__" / "TEST_CASES.md").read_text(encoding="utf-8")
    assert "**覆盖版本：**" not in text
    assert "**版本：** `0.2.0`" in text
    issues = validate_module_doc_versions(info_paths=[info])
    assert issues == []


def test_changelog_head_must_match_version(tmp_path: Path) -> None:
    info = _write_mod(tmp_path, changelog_ver="0.1.0")
    issues = validate_module_info_changelog(info_paths=[info])
    assert issues
    assert any("changelog[0]" in x for x in issues)
