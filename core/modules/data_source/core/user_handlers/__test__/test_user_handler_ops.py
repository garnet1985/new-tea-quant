"""DataSourceHandlerOps：userspace scaffold + mapping + validate。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.data_source import DataSourceManager


@pytest.fixture()
def handlers_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    root = tmp_path / "extensions" / "data_source"
    handlers = root / "handlers"
    template = handlers / "_template" / "example"
    template.mkdir(parents=True)
    (template / "handler.py").write_text(
        "from core.modules.data_source.contracts import DataSourceHooks\n"
        "\n"
        "class ExampleHooks(DataSourceHooks):\n"
        "    pass\n",
        encoding="utf-8",
    )
    (template / "settings.py").write_text(
        "# template placeholder\n",
        encoding="utf-8",
    )
    mapping = root / "mapping.py"
    mapping.write_text(
        '"""test mapping"""\n'
        "DATA_SOURCES = {\n"
        '    "stock_list": {\n'
        '        "handler": "stock_list.StockListHooks",\n'
        '        "is_enabled": True,\n'
        "        \"weight\": 100,\n"
        "    },\n"
        "}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_data_source_handlers_directory",
        lambda: handlers,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_data_source_mapping_path",
        lambda: mapping,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_data_source_root",
        lambda: root,
    )
    return {"handlers": handlers, "mapping": mapping}


def test_scaffold_user_handler(handlers_env: dict[str, Path]) -> None:
    out = DataSourceManager.scaffold_user_handler(key="my_src")
    assert out.get("ok") is True, out
    dest = handlers_env["handlers"] / "my_src"
    text = (dest / "handler.py").read_text(encoding="utf-8")
    assert "MySrcHooks" in text
    assert "ExampleHooks" not in text
    assert out.get("handler") == "my_src.MySrcHooks"
    assert out.get("mapping_key") == "my_src"


def test_scaffold_rejects_existing(handlers_env: dict[str, Path]) -> None:
    assert DataSourceManager.scaffold_user_handler(key="dup").get("ok") is True
    again = DataSourceManager.scaffold_user_handler(key="dup")
    assert again.get("ok") is False


def test_write_and_register_and_validate_missing_table(
    handlers_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert DataSourceManager.scaffold_user_handler(key="cust_feed").get("ok") is True

    settings = (
        "settings = {\n"
        '    "table": "cust_data_feed",\n'
        '    "renew": {\n'
        '        "type": "refresh",\n'
        "    },\n"
        '    "apis": {\n'
        '        "demo": {\n'
        '            "provider_name": "ntq",\n'
        '            "method": "get_x",\n'
        "        },\n"
        "    },\n"
        "}\n"
    )
    written = DataSourceManager.write_user_handler_files(
        key="cust_feed",
        settings_py=settings,
    )
    assert written.get("ok") is True, written

    registered = DataSourceManager.apply_mapping_entry(
        key="cust_feed",
        handler="cust_feed.CustFeedHooks",
        is_enabled=False,
    )
    assert registered.get("ok") is True, registered
    mapping_text = handlers_env["mapping"].read_text(encoding="utf-8")
    assert "cust_feed" in mapping_text

    class _Hooks:
        pass

    class _FakeDM:
        def get_table(self, _name: str):
            return None

    monkeypatch.setattr(
        "core.modules.data_source.core.user_handlers.ops."
        "DataSourceManagerHelper.find_handler_class_from_mappings",
        staticmethod(lambda _mapping, _name: _Hooks),
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.user_handlers.ops."
        "DataSourceManagerHelper.is_valid_handler",
        staticmethod(lambda _cls: True),
    )
    monkeypatch.setattr(
        "core.modules.data_manager.DataManager.get_instance",
        lambda: _FakeDM(),
    )
    checked = DataSourceManager.validate_user_handler(key="cust_feed")
    assert checked.get("ok") is False
    assert any("绑定表未注册" in e for e in checked.get("errors") or [])
