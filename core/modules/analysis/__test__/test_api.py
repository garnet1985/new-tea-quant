"""API contract tests for modules.analysis Facade（对齐 API.md）。"""

from __future__ import annotations

import inspect
import unittest

import pytest

from core.modules.analysis import Analysis
from core.modules.analysis import contracts as analysis_contracts

pytestmark = pytest.mark.force_run


class TestAnalysisApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.analysis as pkg

        self.assertEqual(pkg.__all__, ["Analysis"])
        self.assertIs(pkg.Analysis, Analysis)
        self.assertFalse(hasattr(pkg, "AnalyzeService"))

    def test_no_behavior_api(self) -> None:
        public = [
            name
            for name, value in inspect.getmembers(Analysis)
            if not name.startswith("_") and inspect.isfunction(value)
        ]
        self.assertEqual(public, [])

    def test_contracts_empty(self) -> None:
        self.assertEqual(list(analysis_contracts.__all__), [])


if __name__ == "__main__":
    unittest.main()
