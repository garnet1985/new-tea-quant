#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import logging


logger = logging.getLogger(__name__)


class ReportBuilder:
    @staticmethod
    def write_json(output_path: Path, report: Dict[str, Any]) -> None:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info("[ReportBuilder] JSON report saved: %s", output_path)

    @staticmethod
    def write_markdown_statistical(output_path: Path, report: Dict[str, Any]) -> None:
        lines = [
            "# Statistical Analysis Report",
            "",
            f"**Strategy**: {report.get('strategy_name', 'N/A')}",
            f"**Simulator**: {report.get('sim_type', 'N/A')}",
            f"**Version Dir**: {report.get('sim_version_dir', 'N/A')}",
            "",
            "---",
            "",
        ]
        metrics = report.get("metrics", {})
        if not metrics:
            lines.append("No metrics were calculated.")
        else:
            if "win_rate_distribution" in metrics:
                lines.extend(
                    [
                        "## Win Rate Distribution (by ROI bucket)",
                        "",
                        "| ROI Bucket | Count | Win Rate | Avg ROI |",
                        "|---|---:|---:|---:|",
                    ]
                )
                for bucket in metrics["win_rate_distribution"].get("buckets", []):
                    lines.append(
                        f"| {bucket['bucket']} | {bucket['total_count']} | "
                        f"{bucket['win_rate']:.2%} | {bucket['avg_roi']:.4f} |"
                    )
                lines.append("")
        with output_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("[ReportBuilder] Markdown report saved: %s", output_path)

    @staticmethod
    def write_markdown_ml(output_path: Path, report: Dict[str, Any]) -> None:
        lines = [
            "# ML Factor Importance Report",
            "",
            f"**Model**: {report.get('model', 'N/A')}",
            f"**Task**: {report.get('task', 'N/A')}",
            f"**Samples**: {report.get('n_samples', 0)}",
            f"**Features**: {report.get('n_features', 0)}",
            "",
            "---",
            "",
        ]
        if "error" in report:
            lines.append(f"**Error**: {report.get('message', 'Unknown error')}")
        else:
            perf = report.get("model_performance", {})
            if perf:
                lines.extend(["## Model Performance", "", f"- **Accuracy**: {perf.get('accuracy', 0):.2%}", ""])
            feature_importance = report.get("feature_importance", [])
            if feature_importance:
                lines.extend(["## Top 10 Feature Importance", "", "| Rank | Feature | Importance |", "|---:|---|---:|"])
                for feat in feature_importance[:10]:
                    lines.append(f"| {feat['rank']} | {feat['name']} | {feat['importance']:.6f} |")
                lines.append("")
        with output_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("[ReportBuilder] Markdown report saved: %s", output_path)


__all__ = ["ReportBuilder"]
