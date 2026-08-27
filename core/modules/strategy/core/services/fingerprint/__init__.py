"""模拟身份指纹服务：收集 input → 产出 settings_fp / env_fp。"""

from .fingerprint import FingerprintCalculator, FingerprintResult

__all__ = ["FingerprintCalculator", "FingerprintResult"]
