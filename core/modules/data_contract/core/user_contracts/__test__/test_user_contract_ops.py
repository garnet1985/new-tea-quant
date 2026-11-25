"""UserContractOps：userspace scaffold + data_keys + validate。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.data_contract import ContractIssuer


@pytest.fixture()
def contract_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    root = tmp_path / "extensions" / "data_contract"
    example = root / "contract_example"
    example.mkdir(parents=True)
    (example / "declaration.py").write_text(
        "MY_CUSTOM_DATA_DECLARATION = {}\n",
        encoding="utf-8",
    )
    (example / "loader.py").write_text(
        "from core.modules.data_contract.contracts import BaseDataContractLoader\n"
        "class MyCustomDataLoader(BaseDataContractLoader):\n"
        "    def load(self, params):\n"
        "        return []\n",
        encoding="utf-8",
    )
    (root / "data_keys.py").write_text(
        '"""user keys"""\n\n'
        "class USER_DATA_KEY:\n"
        '    """keys"""\n'
        "\n"
        "__all__ = ['USER_DATA_KEY']\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_data_contract_root",
        lambda: root,
    )
    return {"root": root}


def test_scaffold_user_contract(contract_env: dict[str, Path]) -> None:
    out = ContractIssuer.scaffold_user_contract(
        key="my_feed",
        data_key="my.feed.data",
        display_name="我的 feed",
    )
    assert out.get("ok") is True, out
    dest = contract_env["root"] / "my_feed"
    text = (dest / "declaration.py").read_text(encoding="utf-8")
    assert "MY_FEED_DATA_DECLARATION" in text
    assert '"key": \'my.feed.data\'' in text or '"key": "my.feed.data"' in text
    assert "MyFeedLoader" in (dest / "loader.py").read_text(encoding="utf-8")
    assert out.get("const_name") == "MY_FEED_DATA"


def test_scaffold_rejects_template_name(contract_env: dict[str, Path]) -> None:
    out = ContractIssuer.scaffold_user_contract(key="contract_example")
    assert out.get("ok") is False


def test_register_and_validate_without_reload(
    contract_env: dict[str, Path],
) -> None:
    created = ContractIssuer.scaffold_user_contract(
        key="alpha",
        data_key="user.alpha.data",
    )
    assert created.get("ok") is True, created

    registered = ContractIssuer.apply_user_data_key(
        const_name="USER_ALPHA_DATA",
        data_key="user.alpha.data",
    )
    assert registered.get("ok") is True, registered
    keys_text = (contract_env["root"] / "data_keys.py").read_text(encoding="utf-8")
    assert "USER_ALPHA_DATA" in keys_text
    assert "user.alpha.data" in keys_text

    checked = ContractIssuer.validate_user_contract(key="alpha", reload=False)
    assert checked.get("ok") is True, checked
    assert checked.get("data_key") == "user.alpha.data"
