#!/usr/bin/env python3
"""
ReportBuilder - 报告生成器

职责：
- 将分析器返回的 dict 报告序列化为 JSON 文件
- 生成可读的 Markdown 概览
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import logging


logger = logging.getLogger(__name__)


class ReportBuilder:
    """报告生成器（静态方法类）。"""

    @staticmethod
    def write_json(output_path: Path, report: Dict[str, Any]) -> None:
        """
        将报告写入 JSON 文件。

        Args:
            output_path: 输出文件路径
            report: 报告字典
        """
        try:
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info("[ReportBuilder] JSON 报告已保存: %s", output_path)
        except Exception as exc:
            logger.warning("[ReportBuilder] 保存 JSON 报告失败: %s", exc)
            raise

    @staticmethod
    def write_markdown_statistical(
        output_path: Path, report: Dict[str, Any]
    ) -> None:
        """
        生成统计学分析的 Markdown 报告。

        Args:
            output_path: 输出文件路径
            report: 统计学分析报告字典
        """
        lines = [
            "# 统计学分析报告",
            "",
            f"**策略名称**: {report.get('strategy_name', 'N/A')}",
            f"**模拟器类型**: {report.get('sim_type', 'N/A')}",
            f"**版本目录**: {report.get('sim_version_dir', 'N/A')}",
            "",
            "---",
            "",
        ]

        metrics = report.get("metrics", {})
        if not metrics:
            lines.append("未计算任何指标。")
        else:
            # 胜率分布
            if "win_rate_distribution" in metrics:
                lines.append("## 胜率分布（按 ROI 分桶）")
                lines.append("")
                lines.append("| ROI 区间 | 样本数 | 胜率 | 平均 ROI |")
                lines.append("|---------|--------|------|----------|")
                for bucket in metrics["win_rate_distribution"].get("buckets", []):
                    lines.append(
                        f"| {bucket['bucket']} | {bucket['total_count']} | "
                        f"{bucket['win_rate']:.2%} | {bucket['avg_roi']:.4f} |"
                    )
                lines.append("")

            # 盈亏分布
            if "pnl_distribution" in metrics:
                lines.append("## 盈亏分布")
                lines.append("")
                stats = metrics["pnl_distribution"].get("statistics", {})
                lines.append(f"- **最小值**: {stats.get('min', 0):.4f}")
                lines.append(f"- **最大值**: {stats.get('max', 0):.4f}")
                lines.append(f"- **平均值**: {stats.get('mean', 0):.4f}")
                lines.append(f"- **中位数**: {stats.get('median', 0):.4f}")
                lines.append(f"- **标准差**: {stats.get('std', 0):.4f}")
                lines.append("")

            # 月度表现
            if "monthly_performance" in metrics:
                lines.append("## 月度表现")
                lines.append("")
                lines.append("| 月份 | 交易次数 | 胜率 | 平均 ROI | 总收益 |")
                lines.append("|------|---------|------|----------|--------|")
                for month in metrics["monthly_performance"].get("monthly_stats", []):
                    lines.append(
                        f"| {month['period']} | {month['total_trades']} | "
                        f"{month['win_rate']:.2%} | {month['avg_roi']:.4f} | "
                        f"{month['total_profit']:.2f} |"
                    )
                lines.append("")

            # 年度表现
            if "yearly_performance" in metrics:
                lines.append("## 年度表现")
                lines.append("")
                lines.append("| 年份 | 交易次数 | 胜率 | 平均 ROI | 总收益 | 最大回撤 |")
                lines.append("|------|---------|------|----------|--------|----------|")
                for year in metrics["yearly_performance"].get("yearly_stats", []):
                    lines.append(
                        f"| {year['year']} | {year['total_trades']} | "
                        f"{year['win_rate']:.2%} | {year['avg_roi']:.4f} | "
                        f"{year['total_profit']:.2f} | {year['max_drawdown']:.4f} |"
                    )
                lines.append("")

            # 最大回撤
            if "max_drawdown" in metrics:
                md_info = metrics["max_drawdown"]
                lines.append("## 最大回撤")
                lines.append("")
                lines.append(
                    f"- **最大回撤**: {md_info.get('max_drawdown', 0):.4f}"
                )
                lines.append(
                    f"- **回撤日期**: {md_info.get('max_drawdown_date', 'N/A')}"
                )
                lines.append("")

            # 持仓天数分桶
            if "holding_period_bucket" in metrics:
                lines.append("## 持仓天数分桶统计")
                lines.append("")
                lines.append("| 持仓区间 | 样本数 | 胜率 | 平均 ROI |")
                lines.append("|---------|--------|------|----------|")
                for bucket in metrics["holding_period_bucket"].get("buckets", []):
                    lines.append(
                        f"| {bucket['bucket']} | {bucket['total_count']} | "
                        f"{bucket['win_rate']:.2%} | {bucket['avg_roi']:.4f} |"
                    )
                lines.append("")

        try:
            with output_path.open("w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            logger.info("[ReportBuilder] Markdown 报告已保存: %s", output_path)
        except Exception as exc:
            logger.warning("[ReportBuilder] 保存 Markdown 报告失败: %s", exc)
            raise

    @staticmethod
    def write_markdown_ml(output_path: Path, report: Dict[str, Any]) -> None:
        """
        生成 ML 分析的 Markdown 报告。

        Args:
            output_path: 输出文件路径
            report: ML 分析报告字典
        """
        lines = [
            "# ML 因子重要性分析报告",
            "",
            f"**模型**: {report.get('model', 'N/A')}",
            f"**任务类型**: {report.get('task', 'N/A')}",
            f"**样本数**: {report.get('n_samples', 0)}",
            f"**特征数**: {report.get('n_features', 0)}",
            "",
            "---",
            "",
        ]

        # 错误情况
        if "error" in report:
            lines.append(f"**错误**: {report.get('message', 'Unknown error')}")
            try:
                with output_path.open("w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
            except Exception as exc:
                logger.warning("[ReportBuilder] 保存 Markdown 报告失败: %s", exc)
            return

        # 模型表现
        perf = report.get("model_performance", {})
        if perf:
            lines.append("## 模型表现")
            lines.append("")
            lines.append(f"- **准确率**: {perf.get('accuracy', 0):.2%}")
            lines.append("")

        # 特征重要性 Top 10
        feature_importance = report.get("feature_importance", [])
        if feature_importance:
            lines.append("## 特征重要性 Top 10")
            lines.append("")
            lines.append("| 排名 | 特征名称 | 重要性 |")
            lines.append("|------|---------|--------|")
            for feat in feature_importance[:10]:
                lines.append(
                    f"| {feat['rank']} | {feat['name']} | {feat['importance']:.6f} |"
                )
            lines.append("")

            # 自然语言摘要
            if feature_importance:
                top_feat = feature_importance[0]
                lines.append("## 分析摘要")
                lines.append("")
                lines.append(
                    f"**{top_feat['name']}** 是当前模型中最重要的因子，"
                    f"重要性为 {top_feat['importance']:.4f}。"
                )
                if len(feature_importance) > 1:
                    second_feat = feature_importance[1]
                    lines.append(
                        f"其次是 **{second_feat['name']}** "
                        f"（重要性: {second_feat['importance']:.4f}）。"
                    )
                lines.append("")

        try:
            with output_path.open("w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            logger.info("[ReportBuilder] Markdown 报告已保存: %s", output_path)
        except Exception as exc:
            logger.warning("[ReportBuilder] 保存 Markdown 报告失败: %s", exc)
            raise
