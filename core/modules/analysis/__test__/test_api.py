"""API contract tests for modules.analysis Facade."""

from __future__ import annotations

import unittest

import pytest

from core.modules.analysis import Analysis
from core.modules.analysis import contracts as analysis_contracts

pytestmark = pytest.mark.force_run


class TestAnalysisApi(unittest.TestCase):
    def test_facade_exports(self) -> None:
        import core.modules.analysis as pkg

        self.assertEqual(pkg.__all__, ["Analysis"])
        self.assertIs(pkg.Analysis, Analysis)

    def test_classical_namespace(self) -> None:
        self.assertEqual(Analysis.Classical.__name__, "Classical")
        self.assertEqual(Analysis.ML.__name__, "ML")
        self.assertTrue(callable(Analysis.Classical.quantile_buckets))
        self.assertTrue(callable(Analysis.ML.xgb_feature_importance))
        self.assertTrue(callable(Analysis.ML.xgb_win_classifier))

    def test_quantile_buckets_ok(self) -> None:
        out = Analysis.Classical.quantile_buckets(
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