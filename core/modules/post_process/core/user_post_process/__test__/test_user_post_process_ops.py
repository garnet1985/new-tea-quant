"""UserPostProcessOps：scaffold adapter + post_processor。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.post_process import PostProcess


@pytest.fixture()
def pp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    root = tmp_path / "extensions" / "post_process"
    adapters = root / "adapters"
    processors = root / "post_processors"
    tmpl_a = root / "_template" / "empty_adapter"
    tmpl_p = root / "_template" / "empty_post_processor"
    tmpl_a.mkdir(parents=True)
    tmpl_p.mkdir(parents=True)
    (tmpl_a / "adapter.py").write_text(
        "from core.modules.post_process.contracts import BaseAdapter, ScanSessionReport\n"
        "from typing import Any, Dict\n"
        "class EmptyAdapter(BaseAdapter):\n"
        "    def run(self, session: ScanSessionReport, config: Dict[str, Any], deps: Dict[str, Any]):\n"
        "        return None\n",
        encoding="utf-8",
    )
    (tmpl_a / "settings.py").write_text(
        'settings = {"display_name": "空"}\n',
        encoding="utf-8",
    )
    (tmpl_p / "post_processor.yaml").write_text(
        "key: empty_post_processor\n"
        "name: 空\n"
        "is_enabled: false\n"
        "adapters: {}\n",
        encoding="utf-8",
    )
    adapters.mkdir(parents=True, exist_ok=True)
    processors.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_post_process_extensions_directory",
        lambda: root,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_adapters_directory",
        lambda: adapters,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_post_processors_directory",
        lambda: processors,
    )
    return {"root": root, "adapters": adapters, "processors": processors}


def test_scaffold_adapter(pp_env: dict[str, Path]) -> None:
    out = PostProcess.scaffold_user_adapter(name="my_notify", display_name="通知")
    assert out.get("ok") is True, out
    text = (pp_env["adapters"] / "my_notify" / "adapter.py").read_text(encoding="utf-8")
    assert "MyNotifyAdapter" in text
    assert "EmptyAdapter" not in text


def test_scaffold_and_write_processor(pp_env: dict[str, Path]) -> None:
    created = PostProcess.scaffold_user_post_processor(
        key="my_pipe",
        adapter_name="my_notify",
    )
    assert created.get("ok") is True, created
    path = pp_env["processors"] / "my_pipe" / "post_processor.yaml"
    assert path.is_file()
    assert "my_notify" in path.read_text(encoding="utf-8")

    written = PostProcess.write_user_post_processor_yaml(
        key="my_pipe",
        yaml_body=(
            "key: wrong\n"
            "name: 管线\n"
            "is_enabled: false\n"
            "adapters:\n"
            "  my_notify:\n"
            "    config: {}\n"
        ),
    )
    assert written.get("ok") is True, written
    text = path.read_text(encoding="utf-8")
    assert "key: my_pipe" in text


def test_validate_adapter_with_mock(
    pp_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert PostProcess.scaffold_user_adapter(name="ok_ad").get("ok") is True
    from core.modules.post_process.core import adapter_validator as av

    monkeypatch.setattr(
        av.AdapterValidator,
        "validate",
        staticmethod(lambda _name: (True, "")),
    )
    checked = PostProcess.validate_user_adapter(name="ok_ad")
    assert checked.get("ok") is True, checked
