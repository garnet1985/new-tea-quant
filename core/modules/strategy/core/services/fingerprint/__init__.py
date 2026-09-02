"""模拟身份指纹：``execute_fp`` / ``env_fp``。

白名单见 ``execute_fp_whitelist.py``；哈希由 ``FingerprintCalculator`` 完成。
"""

from .fingerprint import FingerprintCalculator, FingerprintResult

__all__ = ["FingerprintCalculator", "FingerprintResult"]
