"""API contract tests for modules.adapter Facade."""

from __future__ import annotations

import unittest

import pytest

from core.modules.adapter import Adapter
from core.modules.adapter.contracts import BaseOpportunityAdapter

pytestmark = pytest.mark.force_run


class TestAdapterApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.adapter as pkg

        self.assertEqual(pkg.__all__, ["Adapter"])
        self.assertFalse(hasattr(pkg, "validate_adapter"))
        self.assertFalse(hasattr(pkg, "BaseOpportunityAdapter"))

    def test_validate_callable(self) -> None:
        self.assertTrue(callable(Adapter.validate))
        self.assertTrue(callable(Adapter.load_class))
        ok, err = Adapter.validate("")
        self.assertFalse(ok)
        self.assertTrue(err)
        self.assertIsNone(Adapter.load_class(""))

    def test_contracts(self) -> None:
        self.assertTrue(issubclass(BaseOpportunityAdapter, object))
        self.assertTrue(callable(BaseOpportunityAdapter.default_output))


if __name__ == "__main__":
    unittest.main()
