"""TagEntityListResolver 单元测试。"""

from types import SimpleNamespace
from typing import Any, Optional, Sequence
from unittest.mock import MagicMock, patch

import pytest

import core.modules.tag.core.services.entity_list.entity_list_resolver as elr
from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.global_based.constants import GLOBAL_ENTITY_ID
from core.modules.tag.core.engines.shared.hooks.hook_params import TagContext
from core.modules.tag.core.engines.shared.hooks.runtime import TagHookRuntime
from core.modules.tag.core.engines.shared.hooks.tag_hooks import TagHooks
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.enums import TagExecutionMode, TagUpdateMode
from core.modules.tag.core.services.entity_list import TagEntityListResolver

pytestmark = pytest.mark.force_run


def _scenario(
    *,
    attach_to_data_key: str = "",
    base_data_key: str = "",
) -> Scenario:
    settings: dict = {}
    if base_data_key:
        settings["data"] = {"base": {"data_key": base_data_key}}
    return Scenario(
        name="demo",
        key="demo",
        execution_mode=TagExecutionMode.ENTITY_BASED.value,
        update_mode=TagUpdateMode.INCREMENTAL.value,
        attach_to_data_key=attach_to_data_key,
        settings=settings,
    )


def _settings() -> TagSettings:
    return TagSettings.from_dict(
        {
            "is_enabled": True,
            "meta": {"key": "demo"},
            "calculation": {
                "update_mode": "incremental",
                "execution": {"mode": "entity_based"},
            },
            "data": {"base": {"data_key": "stock.kline.daily"}},
            "tag_definitions": [{"name": "demo"}],
        },
        tag_key="demo",
    )


class _FilterHooks(TagHooks):
    def to_entity_list(
        self, ctx: TagContext, entity_list: Sequence[str]
    ) -> Sequence[str]:
        _ = ctx
        return [eid for eid in entity_list if eid.endswith(".SZ")] + ["ghost.SH"]

    def calculate_tag(self, ctx: TagContext) -> Optional[dict]:
        _ = ctx
        return None


class TestTagEntityListResolver:
    @patch.object(elr.DataSettings, "is_global", return_value=True)
    def test_global_base_returns_sentinel(self, _mock_global):
        ids = TagEntityListResolver.resolve(
            _scenario(attach_to_data_key="macro.gdp")
        )
        assert ids == [GLOBAL_ENTITY_ID]

    @patch.object(elr.DataSettings, "is_global", return_value=True)
    def test_non_ts_list_base_returns_sentinel(self, _mock_global):
        ids = TagEntityListResolver.resolve(
            _scenario(base_data_key="stock.list")
        )
        assert ids == [GLOBAL_ENTITY_ID]

    @patch.object(elr, "ContractIssuer")
    @patch.object(elr.DataSettings, "is_global", return_value=False)
    def test_entity_based_from_stock_list(self, _mock_global, mock_issuer):
        mock_issuer.get_list_data_key.return_value = "stock.list"
        contract = MagicMock()
        contract.get_data.return_value = [
            {"id": "000001.SZ"},
            {"id": "600000.SH"},
            {},
        ]
        mock_issuer.issue.return_value = contract

        ids = TagEntityListResolver.resolve(
            _scenario(attach_to_data_key="stock.kline.daily")
        )
        assert ids == ["000001.SZ", "600000.SH"]
        mock_issuer.get_list_data_key.assert_called_once_with("stock.kline.daily")
        mock_issuer.issue.assert_called_once_with("stock.list", fill_in_data=True)

    @patch.object(elr, "ContractIssuer")
    @patch.object(elr.DataSettings, "is_global", return_value=False)
    def test_index_base_uses_index_list(self, _mock_global, mock_issuer):
        mock_issuer.get_list_data_key.return_value = "index.list"
        contract = MagicMock()
        contract.get_data.return_value = [
            {"id": "000001.SH"},
            {"id": "399001.SZ"},
        ]
        mock_issuer.issue.return_value = contract

        ids = TagEntityListResolver.resolve(
            _scenario(attach_to_data_key="index.kline.daily")
        )
        assert ids == ["000001.SH", "399001.SZ"]
        mock_issuer.get_list_data_key.assert_called_once_with("index.kline.daily")
        mock_issuer.issue.assert_called_once_with("index.list", fill_in_data=True)

    @patch.object(elr, "ContractIssuer")
    @patch.object(elr.DataSettings, "is_global", return_value=False)
    def test_base_from_settings_data(self, _mock_global, mock_issuer):
        mock_issuer.get_list_data_key.return_value = "index.list"
        contract = MagicMock()
        contract.get_data.return_value = [{"id": "000300.SH"}]
        mock_issuer.issue.return_value = contract

        ids = TagEntityListResolver.resolve(
            _scenario(base_data_key="index.kline.daily")
        )
        assert ids == ["000300.SH"]
        mock_issuer.get_list_data_key.assert_called_once_with("index.kline.daily")

    @patch.object(elr, "ContractIssuer")
    @patch.object(elr.DataSettings, "is_global", return_value=False)
    def test_entity_limit(self, _mock_global, mock_issuer):
        mock_issuer.get_list_data_key.return_value = "stock.list"
        contract = MagicMock()
        contract.get_data.return_value = [{"id": f"{i:06d}.SZ"} for i in range(5)]
        mock_issuer.issue.return_value = contract

        ids = TagEntityListResolver.resolve(
            _scenario(attach_to_data_key="stock.kline.daily"),
            entity_limit=2,
        )
        assert ids == ["000000.SZ", "000001.SZ"]

    @patch.object(elr, "ContractIssuer")
    @patch.object(elr.DataSettings, "is_global", return_value=False)
    def test_load_failure_returns_empty(self, _mock_global, mock_issuer):
        mock_issuer.get_list_data_key.return_value = "stock.list"
        mock_issuer.issue.side_effect = RuntimeError("boom")
        assert (
            TagEntityListResolver.resolve(
                _scenario(attach_to_data_key="stock.kline.daily")
            )
            == []
        )

    @patch.object(elr, "ContractIssuer")
    @patch.object(elr.DataSettings, "is_global", return_value=False)
    def test_to_entity_list_hook_then_limit(
        self, _mock_global, mock_issuer, monkeypatch: pytest.MonkeyPatch
    ):
        mock_issuer.get_list_data_key.return_value = "stock.list"
        contract = MagicMock()
        contract.get_data.return_value = [
            {"id": "600000.SH"},
            {"id": "000002.SZ"},
            {"id": "000001.SZ"},
        ]
        mock_issuer.issue.return_value = contract

        settings = _settings()
        runtime = TagHookRuntime(
            _FilterHooks(), tag_name="demo", settings=settings
        )
        monkeypatch.setattr(
            elr.TagHookRuntime,
            "from_tag_info",
            classmethod(lambda cls, ti, s: (runtime, None)),
        )
        info = SimpleNamespace(
            key="demo",
            unique_relative_path="demo/x",
            hooks_module_path="x",
            hooks_class_name="Y",
        )
        ids = TagEntityListResolver.resolve(
            _scenario(attach_to_data_key="stock.kline.daily"),
            entity_limit=1,
            tag_info=info,
            settings=settings,
            apply_hook=True,
        )
        assert ids == ["000001.SZ"]

    def test_apply_hook_false_skips_hook(self, monkeypatch: pytest.MonkeyPatch):
        called = {"n": 0}

        def boom(*_a: Any, **_k: Any) -> Any:
            called["n"] += 1
            raise AssertionError("should not call hook")

        monkeypatch.setattr(TagEntityListResolver, "_apply_hook", boom)
        with patch.object(elr.DataSettings, "is_global", return_value=False), patch.object(
            elr, "ContractIssuer"
        ) as mock_issuer:
            mock_issuer.get_list_data_key.return_value = "stock.list"
            contract = MagicMock()
            contract.get_data.return_value = [{"id": "000001.SZ"}]
            mock_issuer.issue.return_value = contract
            ids = TagEntityListResolver.resolve(
                _scenario(attach_to_data_key="stock.kline.daily"),
                apply_hook=False,
                tag_info=SimpleNamespace(),
                settings=_settings(),
            )
        assert ids == ["000001.SZ"]
        assert called["n"] == 0
