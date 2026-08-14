#!/usr/bin/env python3
"""CmdLayout.bar_chart unit tests."""

from __future__ import annotations

import io
import unittest

import pytest

from core.infra.cmd_layout import CmdLayout
from core.infra.cmd_layout.bar_chart.bar_chart import BarBucket, BarChart

pytestmark = pytest.mark.force_run


class TestBarChart(unittest.TestCase):
    def test_render_max_bar_full_width_and_pct(self) -> None:
        text = BarChart.render(
            [("win", 40), ("loss", 10)],
            title="胜负",
            width=20,
        )
        lines = text.splitlines()
        self.assertEqual(lines[0], "胜负")
        self.assertIn("[####################]", lines[1])
        self.assertIn("40", lines[1])
        self.assertIn("80.0%", lines[1])
        self.assertIn("10", lines[2])
        self.assertIn("20.0%", lines[2])
        # loss is 1/4 of win → ~5 filled cells
        self.assertRegex(lines[2], r"\[#{5}\s{15}\]")

    def test_label_alignment(self) -> None:
        text = BarChart.render(
            [("a", 1), ("longer", 2)],
            width=10,
            show_pct=False,
        )
        lines = text.splitlines()
        # labels padded to same width before the bar
        self.assertTrue(lines[0].startswith("  a       "))
        self.assertTrue(lines[1].startswith("  longer  "))

    def test_negative_value_clamped(self) -> None:
        bucket = BarBucket("x", -5)
        self.assertEqual(bucket.value, 0.0)
        text = BarChart.render([("ok", 5), ("neg", -3)], width=10, show_pct=False)
        self.assertIn("[##########]", text.splitlines()[0])
        self.assertIn("[          ]", text.splitlines()[1])

    def test_all_zero_buckets(self) -> None:
        text = BarChart.render([("a", 0), ("b", 0)], width=8)
        for line in text.splitlines():
            self.assertIn("[########]", line)
            self.assertIn("0.0%", line)

    def test_from_values_empty(self) -> None:
        self.assertEqual(BarChart.from_values([], title="ROI"), "ROI")
        self.assertEqual(BarChart.from_values([]), "")

    def test_from_values_single_value(self) -> None:
        text = BarChart.from_values([1.5, 1.5, 1.5], bins=5, title="X", label_format=".1f")
        lines = text.splitlines()
        self.assertEqual(lines[0], "X")
        self.assertEqual(len(lines), 2)
        self.assertIn("[1.5]", lines[1])
        self.assertIn("3", lines[1])
        self.assertIn("100.0%", lines[1])

    def test_from_values_multi_bins_labels(self) -> None:
        values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        text = BarChart.from_values(values, bins=2, label_format=".1f", width=10)
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("[0.0, 0.5)", lines[0])
        self.assertIn("[0.5, 1.0]", lines[1])

    def test_ascii_only_output(self) -> None:
        text = BarChart.from_values(
            [-0.05, 0.0, 0.02, 0.08, 0.1],
            bins=4,
            title="ROI",
            width=12,
        )
        forbidden = ("█", "░", "▓", "📊", "■", "□")
        for ch in forbidden:
            self.assertNotIn(ch, text)
        # bar body uses only # and space inside the chart brackets (last [...])
        for line in text.splitlines()[1:]:
            start = line.rindex("[")
            end = line.index("]", start)
            body = line[start + 1 : end]
            self.assertTrue(set(body) <= {"#", " "}, body)

    def test_print_to_stream(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.bar_chart.print(
            [("a", 2), ("b", 1)],
            title="T",
            width=4,
            stream=buf,
        )
        self.assertEqual(buf.getvalue().rstrip("\n"), returned)
        self.assertIn("T", returned)

    def test_print_from_values(self) -> None:
        buf = io.StringIO()
        returned = CmdLayout.bar_chart.print_from_values(
            [1.0, 2.0, 3.0],
            bins=3,
            title="H",
            stream=buf,
        )
        self.assertIn("H", returned)
        self.assertEqual(buf.getvalue().rstrip("\n"), returned)

    def test_mapping_and_barbucket_input(self) -> None:
        text = BarChart.render(
            [
                BarBucket("x", 3),
                {"label": "y", "count": 1},
            ],
            width=6,
            show_pct=False,
        )
        self.assertIn("x", text)
        self.assertIn("y", text)


if __name__ == "__main__":
    unittest.main()
