"""Cache/report payload helper for strategy workbench."""

import json

from core.infra.project_context.path_manager import PathManager


class StrategyWorkbenchCacheHelper:
    """Shared helpers for cache payload coercion and enum report loading."""

    @staticmethod
    def _sanitize_enum_payload_for_snapshot(enum_payload: dict) -> dict:
        payload = dict(enum_payload or {})
        payload.pop("stockRows", None)
        return payload

    @staticmethod
    def _coerce_db_settings_snapshot(raw):
        if raw is None:
            return None
        if isinstance(raw, dict):
            return raw if raw else None
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return None
            if isinstance(parsed, dict) and parsed:
                return parsed
        return None

    @staticmethod
    def _coerce_db_result_summary(raw):
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    @staticmethod
    def _enum_summary_row_to_bff_payload(row: dict) -> dict:
        if not isinstance(row, dict):
            row = {}
        out = {
            "opportunities": int(row.get("opportunities") or 0),
            "totalStocks": int(row.get("totalStocks") or 0),
            "triggerStocks": int(row.get("triggerStocks") or 0),
            "completedCount": int(row.get("completedCount") or 0),
            "unfinishedCount": int(row.get("unfinishedCount") or 0),
            "completionRate": float(row.get("completionRate") or 0.0),
        }
        version_dir = str(row.get("version_dir") or "").strip()
        if version_dir:
            out["versionDir"] = version_dir
        enum_metrics = row.get("enumMetrics")
        if isinstance(enum_metrics, dict):
            out["enumMetrics"] = enum_metrics
        stock_rows = row.get("stockRows")
        if isinstance(stock_rows, list):
            out["stockRows"] = stock_rows
        return out

    @staticmethod
    def _resolve_enum_output_dir(strategy_name: str, version_dir_name: str):
        if not version_dir_name:
            return None
        output_candidate = PathManager.strategy_opportunity_enums(
            strategy_name, use_sampling=False
        ) / version_dir_name
        if output_candidate.exists() and output_candidate.is_dir():
            return output_candidate
        sampling_candidate = PathManager.strategy_opportunity_enums(
            strategy_name, use_sampling=True
        ) / version_dir_name
        if sampling_candidate.exists() and sampling_candidate.is_dir():
            return sampling_candidate
        return None

    def _load_enum_report_from_output(self, strategy_name: str, enum_payload: dict) -> dict:
        version_dir_name = str(enum_payload.get("versionDir") or "").strip()
        output_dir = self._resolve_enum_output_dir(strategy_name, version_dir_name)
        if output_dir is None:
            return {}
        try:
            report_file = output_dir / "0_report_enum.json"
            if not report_file.exists():
                return {}
            payload = json.loads(report_file.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}
