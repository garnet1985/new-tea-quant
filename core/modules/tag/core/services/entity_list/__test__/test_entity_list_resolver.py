"""TagEntityListResolver 单元测试。"""

from unittest.mock import MagicMock, patch

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.enums import TagExecutionMode, TagUpdateMode
from core.modules.tag.core.services.entity_list import TagEntityListResolver


def _scenario(*, tag_target_type: str = "entity_based") -> Scenario:
    return Scenario(
        name="demo",
        key="demo",
        execution_mode=TagExecutionMode.ENTITY_BASED.value,
        update_mode=TagUpdateMode.INCREMENTAL.value,
        settings={"tag_target_type": tag_target_type},
    )


class TestTagEntityListResolver:
    def test_general_returns_sentinel(self):
        ids = TagEntityListResolver.resolve(_scenario(tag_target_type="general"))
        assert ids == ["__general__"]

    @patch("core.modules.tag.core.services.entity_list.entity_list_resolver.ContractIssuer")
    def test_entity_based_from_stock_list(self, mock_issuer):
        contract = MagicMock()
        contract.get_data.return_value = [
            {"id": "000001.SZ"},
            {"id": "600000.SH"},
            {},
        ]
        mock_issuer.issue.return_value = contract

        ids = TagEntityListResolver.resolve(_scenario())
        assert ids == ["000001.SZ", "600000.SH"]

    @patch("core.modules.tag.core.services.entity_list.entity_list_resolver.ContractIssuer")
    def test_stock_limit(self, mock_issuer):
        contract = MagicMock()
        contract.get_data.return_value = [{"id": f"{i:06d}.SZ"} for i in range(5)]
        mock_issuer.issue.return_value = contract

        ids = TagEntityListResolver.resolve(_scenario(), stock_limit=2)
        assert ids == ["000000.SZ", "000001.SZ"]

    @patch("core.modules.tag.core.services.entity_list.entity_list_resolver.ContractIssuer")
    def test_load_failure_returns_empty(self, mock_issuer):
        mock_issuer.issue.side_effect = RuntimeError("boom")
        assert TagEntityListResolver.resolve(_scenario()) == []
