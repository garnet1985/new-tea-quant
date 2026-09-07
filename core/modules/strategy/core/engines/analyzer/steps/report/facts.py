"""Structured attribution facts for BFF / FED — no CLI narrative copy."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .insight import InsightBuilder


class InsightFacts:
    """UI read model extracted from ``analysis/report.json``."""

    @classmethod
    def from_report(cls, report: Dict[str, Any]) -> Dict[str, Any]:
        attribution = (
            report.get("attribution") if isinstance(report.get("attribution"), dict) else {}
        )
        classical = (
            attribution.get("classical") if isinstance(attribution.get("classical"), dict) else {}
        )
        univariate = (
            classical.get("univariate") if isinstance(classical.get("univariate"), dict) else {}
        )
        fields = univariate.get("fields") if isinstance(univariate.get("fields"), dict) else {}
        skip_summary = (
            classical.get("skip_summary")
            if isinstance(classical.get("skip_summary"), dict)
            else {}
        )
        primary = InsightBuilder._pick_primary_field(fields)
        if primary is None:
            return {
                "status": "empty",
                "field_key": None,
                "tiers": [],
                "buckets": [],
                "correlation": None,
                "skip_summary": dict(skip_summary) if skip_summary else None,
                "empty_reason": cls._empty_reason(
                    report, univariate, skip_summary
                ),
                "other_fields": [],
                "run_comparison": cls._run_comparison(classical),
                "multivariate": cls._multivariate(classical),
                "ml": cls._ml(attribution),
                "technical": cls._technical(report, classical, field=None, field_key=None),
            }
        key, field = primary
        buckets = InsightBuilder._extract_buckets(field)
        tiers = InsightBuilder._merge_to_natural_tiers(buckets)
        corr = field.get("correlation") if isinstance(field.get("correlation"), dict) else {}
        return {
            "status": "ok",
            "field_key": key,
            "tiers": list(tiers),
            "buckets": list(buckets),
            "correlation": cls._correlation(corr),
            "skip_summary": dict(skip_summary) if skip_summary else None,
            "other_fields": cls._other_fields(fields, primary_key=key),
            "run_comparison": cls._run_comparison(classical),
            "multivariate": cls._multivariate(classical),
            "ml": cls._ml(attribution),
            "technical": cls._technical(report, classical, field=field, field_key=key),
        }

    @staticmethod
    def _empty_reason(
        report: Dict[str, Any],
        univariate: Dict[str, Any],
        skip_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Why this step has no attributable field — codes for FED, no CLI copy."""
        manifest = report.get("manifest") if isinstance(report.get("manifest"), dict) else {}
        coverage = (
            manifest.get("coverage") if isinstance(manifest.get("coverage"), dict) else {}
        )
        capture_keys = manifest.get("capture_keys")
        if not isinstance(capture_keys, list):
            capture_keys = []
        investment_count = InsightFacts._as_int(
            coverage.get("investment_count"),
            fallback=skip_summary.get("investment_count") if skip_summary else None,
        )
        with_snapshot = InsightFacts._as_int(coverage.get("with_snapshot"))
        uni_reason = str(univariate.get("reason") or "")
        fields = univariate.get("fields") if isinstance(univariate.get("fields"), dict) else {}
        insufficient_field = any(
            isinstance(field, dict) and str(field.get("reason") or "") == "insufficient_samples"
            for field in fields.values()
        )
        has_coverage = (
            "investment_count" in coverage
            or "with_snapshot" in coverage
            or bool(skip_summary)
        )
        if uni_reason == "no_varying_numeric_capture":
            code = "no_capture"
        elif not has_coverage and investment_count <= 0 and with_snapshot <= 0:
            code = "unknown"
        elif investment_count <= 0:
            code = "insufficient_samples"
        elif with_snapshot <= 0:
            code = "no_capture"
        elif with_snapshot < 2 or insufficient_field or uni_reason == "insufficient_samples":
            code = "insufficient_samples"
        else:
            code = "no_capture"
        return {
            "code": code,
            "investment_count": investment_count,
            "with_snapshot": with_snapshot,
            "capture_key_count": len(capture_keys),
        }

    @staticmethod
    def _as_int(value: Any, fallback: Any = None) -> int:
        for raw in (value, fallback):
            if raw is None:
                continue
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
        return 0

    @staticmethod
    def _correlation(corr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not corr:
            return None
        return {
            "status": str(corr.get("status") or ""),
            "rho": corr.get("rho"),
            "p_value": corr.get("p_value"),
        }

    @staticmethod
    def _other_fields(
        fields: Dict[str, Any],
        *,
        primary_key: Optional[str],
    ) -> List[Dict[str, Any]]:
        ranked: List[tuple] = []
        for key, field in fields.items():
            if not isinstance(field, dict) or key == primary_key:
                continue
            corr = field.get("correlation") if isinstance(field.get("correlation"), dict) else {}
            if corr.get("status") != "ok" or corr.get("rho") is None:
                continue
            ranked.append((abs(float(corr["rho"])), str(key), corr))
        ranked.sort(key=lambda item: item[0], reverse=True)
        out: List[Dict[str, Any]] = []
        for _, key, corr in ranked[:4]:
            out.append(
                {
                    "key": key,
                    "status": str(corr.get("status") or "ok"),
                    "rho": corr.get("rho"),
                    "p_value": corr.get("p_value"),
                }
            )
        return out

    @staticmethod
    def _run_comparison(classical: Dict[str, Any]) -> Dict[str, Any]:
        block = (
            classical.get("run_comparison")
            if isinstance(classical.get("run_comparison"), dict)
            else {}
        )
        comparison = (
            block.get("comparison") if isinstance(block.get("comparison"), dict) else {}
        )
        return {
            "status": str(block.get("status") or "not_requested"),
            "reason": block.get("reason"),
            "baseline_version_id": block.get("baseline_version_id")
            or comparison.get("baseline_version_id"),
            "current_version_id": comparison.get("current_version_id"),
            "has_meaningful_diff": comparison.get("has_meaningful_diff"),
            "settings_diff": list(comparison.get("settings_diff") or []),
            "capture_diff": list(comparison.get("capture_diff") or []),
            "coverage_diff": list(comparison.get("coverage_diff") or []),
        }

    @staticmethod
    def _multivariate(classical: Dict[str, Any]) -> Dict[str, Any]:
        block = (
            classical.get("multivariate")
            if isinstance(classical.get("multivariate"), dict)
            else {}
        )
        status = str(block.get("status") or "skipped")
        ranking: List[Dict[str, Any]] = []
        ols = (
            block.get("ols_weighted_roi")
            if isinstance(block.get("ols_weighted_roi"), dict)
            else {}
        )
        logistic = (
            block.get("logistic_win") if isinstance(block.get("logistic_win"), dict) else {}
        )
        kind = None
        coefs: List[Any] = []
        if ols.get("status") == "ok":
            coefs = list(ols.get("coefficients") or [])
            kind = "roi"
        elif logistic.get("status") == "ok":
            coefs = list(logistic.get("coefficients") or [])
            kind = "win"
        scored: List[tuple] = []
        for item in coefs:
            if not isinstance(item, dict) or item.get("coef") is None:
                continue
            scored.append((abs(float(item["coef"])), item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        for _, item in scored[:4]:
            ranking.append(
                {
                    "key": str(item.get("feature") or "?"),
                    "coef": float(item["coef"]),
                    "kind": kind,
                }
            )
        found = block.get("found_features")
        if found is None and block.get("features"):
            found = len(block.get("features") or [])
        return {
            "status": status if status in ("ok", "partial") else "skipped",
            "reason": block.get("reason"),
            "found_features": found,
            "features": list(block.get("features") or []),
            "n": block.get("n"),
            "ranking": ranking,
        }

    @staticmethod
    def _ml(attribution: Dict[str, Any]) -> Dict[str, Any]:
        block = attribution.get("ml") if isinstance(attribution.get("ml"), dict) else {}
        status = str(block.get("status") or "skipped")
        xgb = block.get("xgb") if isinstance(block.get("xgb"), dict) else {}
        ranking: List[Dict[str, Any]] = []
        if status in ("ok", "partial") and xgb.get("status") in ("ok", "partial"):
            for item in list(xgb.get("feature_importance") or [])[:4]:
                if not isinstance(item, dict):
                    continue
                ranking.append(
                    {
                        "key": str(item.get("feature") or "?"),
                        "importance": item.get("importance"),
                    }
                )
            return {
                "status": status,
                "reason": None,
                "ranking": ranking,
            }
        return {
            "status": "skipped",
            "reason": str(block.get("reason") or xgb.get("reason") or "") or None,
            "ranking": [],
        }

    @staticmethod
    def _technical(
        report: Dict[str, Any],
        classical: Dict[str, Any],
        *,
        field: Optional[Dict[str, Any]],
        field_key: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "sample_size": None if field is None else field.get("n"),
            "field_key": field_key,
            "strategy_key": report.get("strategy_key"),
            "step": report.get("step"),
            "version_id": report.get("version_id"),
            "classical_status": classical.get("status"),
        }


__all__ = ["InsightFacts"]
