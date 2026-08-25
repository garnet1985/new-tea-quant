"""API contract tests for modules.analysis Facade."""

from __future__ import annotations

import inspect
import unittest

import pytest

from core.modules.analysis import Analysis, Classical, ML, quantile_buckets
from core.modules.analysis import contracts as analysis_contracts

pytestmark = pytest.mark.force_run


class TestAnalysisApi(unittest.TestCase):
    def test_facade_exports(self) -> None:
        import core.modules.analysis as pkg

        self.assertIn("Analysis", pkg.__all__)
        self.assertIn("quantile_buckets", pkg.__all__)
        self.assertIs(pkg.Analysis, Analysis)

    def test_classical_namespace(self) -> None:
        self.assertIs(Analysis.Classical, Classical)
        self.assertTrue(callable(Analysis.Classical.quantile_buckets))
        self.assertTrue(callable(Analysis.ML.xgb_feature_importance))

    def test_quantile_buckets_ok(self) -> None:
        out = quantile_buckets(
            [1.0, 2.0, 3.0, 4.0],
            [0.1, 0.2, 0.3, 0.4],
            [True, True, False, False],
            n_buckets=2,
            min_bucket_size=2,
        )
        self.assertEqual(out["status"], "ok")

    def test_contracts_empty(self) -> None:
        self.assertEqual(list(analysis_contracts.__all__), [])


if __name__ == "__main__":
    unittest.main()
