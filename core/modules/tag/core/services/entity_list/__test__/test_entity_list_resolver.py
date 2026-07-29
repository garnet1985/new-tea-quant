"""TagEntityListResolver 单元测试。"""

from unittest.mock import MagicMock, patch

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.global_based.constants import GLOBAL_ENTITY_ID
from core.modules.tag.core.enums import TagExecutionMode, TagUpdateMode
from core.modules.tag.core.services.entity_list import TagEntityListResolver


def _scenario(
    *,
    tag_target_type: str = "entity_based",
    attach_to_data_key: str = "",
    base_data_key: str = "",
) -> Scenario:
    settings = {"tag_target_type": tag_target_type}
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


class TestTagEntityListResolver:
    def test_general_returns_sentinel(self):
        ids = TagEntityListResolver.resolve(_scenario(tag_target_type="general"))
        assert ids == [GLOBAL_ENTITY_ID]

    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.DataSettings.is_global",
        return_value=True,
    )
    def test_global_base_returns_sentinel(self, _mock_global):
        ids = TagEntityListResolver.resolve(
            _scenario(attach_to_data_key="macro.gdp")
        )
        assert ids == [GLOBAL_ENTITY_ID]

    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.DataSettings.is_global",
        return_value=False,
    )
    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.ContractIssuer"
    )
    def test_entity_based_from_stock_list(self, mock_issuer, _mock_global):
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

    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.DataSettings.is_global",
        return_value=False,
    )
    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.ContractIssuer"
    )
    def test_index_base_uses_index_list(self, mock_issuer, _mock_global):
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

    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.DataSettings.is_global",
        return_value=False,
    )
    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.ContractIssuer"
    )
    def test_base_from_settings_data(self, mock_issuer, _mock_global):
        mock_issuer.get_list_data_key.return_value = "index.list"
        contract = MagicMock()
        contract.get_data.return_value = [{"id": "000300.SH"}]
        mock_issuer.issue.return_value = contract

        ids = TagEntityListResolver.resolve(
            _scenario(base_data_key="index.kline.daily")
        )
        assert ids == ["000300.SH"]
        mock_issuer.get_list_data_key.assert_called_once_with("index.kline.daily")

    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.DataSettings.is_global",
        return_value=False,
    )
    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.ContractIssuer"
    )
    def test_stock_limit(self, mock_issuer, _mock_global):
        mock_issuer.get_list_data_key.return_value = "stock.list"
        contract = MagicMock()
        contract.get_data.return_value = [{"id": f"{i:06d}.SZ"} for i in range(5)]
        mock_issuer.issue.return_value = contract

        ids = TagEntityListResolver.resolve(
            _scenario(attach_to_data_key="stock.kline.daily"),
            stock_limit=2,
        )
        assert ids == ["000000.SZ", "000001.SZ"]

    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.DataSettings.is_global",
        return_value=False,
    )
    @patch(
        "core.modules.tag.core.services.entity_list.entity_list_resolver.ContractIssuer"
    )
    def test_load_failure_returns_empty(self, mock_issuer, _mock_global):
        mock_issuer.get_list_data_key.return_value = "stock.list"
        mock_issuer.issue.side_effect = RuntimeError("boom")
        assert (
            TagEntityListResolver.resolve(
                _scenario(attach_to_data_key="stock.kline.daily")
            )
            == []
        )
