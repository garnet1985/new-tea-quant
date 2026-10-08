"""XGBoost / SHAP 是选装依赖。导入失败时归因跳过单笔机器学习，而不是中断。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_PACKAGES = ("xgboost", "shap")


def missing_ml_packages() -> List[str]:
    """返回未能导入的包名。缺库、动态库加载失败都算未安装。"""
    missing: List[str] = []
    for name in _PACKAGES:
        try:
            __import__(name)
        except Exception:
            missing.append(name)
    return missing


def ml_appendix_skip(n_versions: int) -> Optional[Dict[str, Any]]:
    """单笔 XGB+SHAP 附录在依赖不齐时的跳过结果；齐了则返回 None，由调用方继续跑。"""
    missing = missing_ml_packages()
    if not missing:
        return None
    return {
        "status": "skipped",
        "reason": "missing_dependency",
        "dependency": "、".join(missing),
        "n": 0,
        "n_versions": int(n_versions),
    }


__all__ = ["missing_ml_packages", "ml_appendix_skip"]
