#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import json
import logging

import numpy as np
import pandas as pd

from .base import AnalysisContext, BaseAnalyzer

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


@dataclass
class MLAnalyzer(BaseAnalyzer):
    task: str = "classification"

    def run(self) -> Dict[str, Any]:
        if not XGBOOST_AVAILABLE:
            return {"error": "xgboost_not_available", "message": "XGBoost not installed"}
        df = self._load_enumerator_data()
        if df is None or df.empty:
            return {"error": "no_data", "message": "Unable to load enumerator data"}
        X, y, feature_names = self._prepare_features_and_labels(df)
        if X is None or y is None:
            return {"error": "feature_preparation_failed", "message": "Feature preparation failed"}
        model = self._train_model(X, y)
        return {
            "model": "xgboost",
            "task": self.task,
            "n_samples": len(X),
            "n_features": len(feature_names),
            "feature_importance": self._extract_feature_importance(model, feature_names),
            "model_performance": self._calculate_model_performance(model, X, y),
        }

    def _load_enumerator_data(self) -> pd.DataFrame | None:
        metadata_path = self.context.sim_version_dir / "metadata.json"
        if not metadata_path.exists():
            metadata_path = self.context.sim_version_dir / "0_metadata.json"
        if not metadata_path.exists():
            return None
        try:
            with metadata_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
            output_version_info = metadata.get("output_version", {})
            output_root_raw = output_version_info.get("output_root", "")
            version_dir = output_version_info.get("version_dir", "")
            if not output_root_raw or not version_dir:
                return None
            output_root = Path(output_root_raw)
            if not output_root.is_absolute():
                # Reconstruct via PathManager if metadata stores subdir ("test"/"output")
                from core.infra.project_context import PathManager

                use_sampling = str(output_root_raw).strip().lower() == "test"
                output_root = PathManager.strategy_opportunity_enums(
                    self.context.strategy_name, use_sampling=use_sampling
                )
            output_version_dir = output_root / version_dir
            records: List[Dict[str, Any]] = []
            for csv_file in output_version_dir.glob("*_opportunities.csv"):
                try:
                    records.extend(pd.read_csv(csv_file).to_dict("records"))
                except Exception as exc:
                    logger.warning("[MLAnalyzer] Failed loading %s: %s", csv_file, exc)
            return pd.DataFrame(records) if records else None
        except Exception:
            return None

    def _prepare_features_and_labels(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame | None, pd.Series | None, List[str]]:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_cols = ["opportunity_id", "stock_id", "trigger_date", "exit_date", "start_date", "end_date"]
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        if not feature_cols:
            return None, None, []
        X = df[feature_cols].fillna(0)
        if "is_win" in df.columns:
            y = df["is_win"].astype(int)
        elif "exit_roi" in df.columns:
            y = (df["exit_roi"] > 0).astype(int)
        elif "roi" in df.columns:
            y = (df["roi"] > 0).astype(int)
        else:
            return None, None, []
        valid_mask = ~y.isna()
        X = X[valid_mask]
        y = y[valid_mask]
        return (X, y, feature_cols) if len(X) > 0 else (None, None, [])

    def _train_model(self, X: pd.DataFrame, y: pd.Series) -> Any:
        model = xgb.XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric="logloss"
        )
        model.fit(X, y)
        return model

    def _extract_feature_importance(self, model: Any, feature_names: List[str]) -> List[Dict[str, Any]]:
        pairs = list(zip(feature_names, model.feature_importances_))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return [{"name": name, "importance": round(float(importance), 6), "rank": rank} for rank, (name, importance) in enumerate(pairs, start=1)]

    def _calculate_model_performance(self, model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        from sklearn.metrics import accuracy_score, classification_report

        y_pred = model.predict(X)
        return {
            "accuracy": round(float(accuracy_score(y, y_pred)), 4),
            "classification_report": classification_report(y, y_pred, output_dict=True, zero_division=0),
        }


__all__ = ["MLAnalyzer"]
