#!/usr/bin/env python3
"""
MLAnalyzer - 机器学习分析器（XGBoost）

职责：
- 基于枚举器的机会结果，使用 XGBoost 分析因子重要性
- 第一版只支持二分类任务（win/loss）
- 输出特征重要性榜单
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging

import pandas as pd
import numpy as np

from .base_analyzer import BaseAnalyzer, AnalysisContext


logger = logging.getLogger(__name__)

# 尝试导入 XGBoost，如果失败则标记为不可用
try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning(
        "[MLAnalyzer] XGBoost 未安装，ML 分析功能将不可用。"
        "请运行: pip install xgboost"
    )


@dataclass
class MLAnalyzer(BaseAnalyzer):
    """
    机器学习分析器（XGBoost）。

    第一版只支持：
    - target = "enumerator"：基于枚举器机会结果
    - task = "classification"：二分类（win/loss）
    """

    task: str = "classification"  # 当前只支持 "classification"

    def run(self) -> Dict[str, Any]:
        """
        执行 ML 分析。

        Returns:
            包含因子重要性榜单的报告字典
        """
        if not XGBOOST_AVAILABLE:
            return {
                "error": "xgboost_not_available",
                "message": "XGBoost 未安装，无法执行 ML 分析",
            }

        # 1. 加载枚举器机会数据
        df = self._load_enumerator_data()
        if df is None or df.empty:
            logger.warning("[MLAnalyzer] 无法加载枚举器数据或数据为空")
            return {"error": "no_data", "message": "无法加载枚举器数据"}

        # 2. 构造特征矩阵 X 和标签 y
        X, y, feature_names = self._prepare_features_and_labels(df)
        if X is None or y is None:
            logger.warning("[MLAnalyzer] 无法构造特征或标签")
            return {"error": "feature_preparation_failed", "message": "特征准备失败"}

        # 3. 训练 XGBoost 模型
        try:
            model = self._train_model(X, y)
        except Exception as exc:
            logger.warning("[MLAnalyzer] 模型训练失败: %s", exc)
            return {"error": "training_failed", "message": str(exc)}

        # 4. 提取特征重要性
        feature_importance = self._extract_feature_importance(
            model, feature_names
        )

        # 5. 计算模型表现（简单指标）
        model_performance = self._calculate_model_performance(model, X, y)

        return {
            "model": "xgboost",
            "task": self.task,
            "n_samples": len(X),
            "n_features": len(feature_names),
            "feature_importance": feature_importance,
            "model_performance": model_performance,
        }

    def _load_enumerator_data(self) -> pd.DataFrame | None:
        """
        从枚举器结果加载机会数据。

        需要从模拟器依赖的枚举器输出版本目录读取 opportunities CSV。
        """
        # 从 metadata.json 中获取枚举器输出版本信息
        metadata_path = self.context.sim_version_dir / "metadata.json"
        if not metadata_path.exists():
            logger.warning("[MLAnalyzer] 未找到 metadata.json: %s", metadata_path)
            return None

        try:
            with metadata_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)

            output_version_info = metadata.get("output_version", {})
            if not output_version_info:
                logger.warning("[MLAnalyzer] metadata 中缺少 output_version 信息")
                return None

            # 解析输出版本目录路径
            output_root = Path(output_version_info.get("output_root", ""))
            version_dir = output_version_info.get("version_dir", "")
            if not output_root or not version_dir:
                logger.warning("[MLAnalyzer] 输出版本信息不完整")
                return None

            output_version_dir = output_root / version_dir
            if not output_version_dir.exists():
                logger.warning(
                    "[MLAnalyzer] 输出版本目录不存在: %s", output_version_dir
                )
                return None

            # 加载所有 opportunities CSV
            records: List[Dict[str, Any]] = []
            for csv_file in output_version_dir.glob("*_opportunities.csv"):
                try:
                    df_part = pd.read_csv(csv_file)
                    records.extend(df_part.to_dict("records"))
                except Exception as exc:
                    logger.warning(
                        "[MLAnalyzer] 加载文件 %s 失败: %s", csv_file, exc
                    )

            if not records:
                return None

            return pd.DataFrame(records)
        except Exception as exc:
            logger.warning("[MLAnalyzer] 加载枚举器数据失败: %s", exc)
            return None

    def _prepare_features_and_labels(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame | None, pd.Series | None, List[str]]:
        """
        准备特征矩阵 X 和标签 y。

        Args:
            df: 机会数据 DataFrame

        Returns:
            (X, y, feature_names)
        """
        # 选择数值型特征列
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # 排除明显不是特征的列（如 ID、日期字符串等）
        exclude_cols = [
            "opportunity_id",
            "stock_id",
            "trigger_date",
            "exit_date",
            "start_date",
            "end_date",
        ]
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]

        if not feature_cols:
            logger.warning("[MLAnalyzer] 未找到可用特征列")
            return None, None, []

        X = df[feature_cols].copy()

        # 处理缺失值（简单填充为 0）
        X = X.fillna(0)

        # 构造标签 y（二分类：win/loss）
        # 优先使用已有的结果字段
        if "is_win" in df.columns:
            y = df["is_win"].astype(int)
        elif "exit_roi" in df.columns:
            y = (df["exit_roi"] > 0).astype(int)
        elif "roi" in df.columns:
            y = (df["roi"] > 0).astype(int)
        else:
            logger.warning("[MLAnalyzer] 无法构造标签（缺少结果字段）")
            return None, None, []

        # 移除标签为 NaN 的样本
        valid_mask = ~y.isna()
        X = X[valid_mask]
        y = y[valid_mask]

        if len(X) == 0:
            logger.warning("[MLAnalyzer] 有效样本数为 0")
            return None, None, []

        return X, y, feature_cols

    def _train_model(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Any:  # xgb.XGBClassifier
        """
        训练 XGBoost 分类模型。

        Args:
            X: 特征矩阵
            y: 标签

        Returns:
            训练好的 XGBoost 模型
        """
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost 未安装")

        # 使用默认参数训练（第一版不做参数调优）
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric="logloss",
        )

        model.fit(X, y)

        return model

    def _extract_feature_importance(
        self, model: Any, feature_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        提取并排序特征重要性。

        Args:
            model: 训练好的 XGBoost 模型
            feature_names: 特征名称列表

        Returns:
            按重要性排序的特征列表
        """
        importances = model.feature_importances_

        # 创建 (特征名, 重要性) 对并排序
        feature_importance_pairs = list(zip(feature_names, importances))
        feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)

        # 转换为报告格式
        result = []
        for rank, (name, importance) in enumerate(feature_importance_pairs, start=1):
            result.append(
                {
                    "name": name,
                    "importance": round(float(importance), 6),
                    "rank": rank,
                }
            )

        return result

    def _calculate_model_performance(
        self, model: Any, X: pd.DataFrame, y: pd.Series
    ) -> Dict[str, Any]:
        """
        计算模型表现指标（简单版）。

        Args:
            model: 训练好的模型
            X: 特征矩阵
            y: 标签

        Returns:
            包含 accuracy 等指标的字典
        """
        from sklearn.metrics import accuracy_score, classification_report

        y_pred = model.predict(X)
        accuracy = accuracy_score(y, y_pred)

        # 获取分类报告（转换为字典）
        report_dict = classification_report(
            y, y_pred, output_dict=True, zero_division=0
        )

        return {
            "accuracy": round(float(accuracy), 4),
            "classification_report": report_dict,
        }
