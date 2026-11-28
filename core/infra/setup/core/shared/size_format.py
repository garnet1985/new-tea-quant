"""安装/导入展示用的体积文案。"""

from __future__ import annotations


def format_mb_fraction(size_bytes: int) -> str:
    """固定一位小数的 MB 数值（不含单位后缀）。"""
    return f"{max(0, int(size_bytes or 0)) / (1024 * 1024):.1f}"


def format_size_label(size_bytes: int) -> str:
    """自适应 B / KB / MB 标签。"""
    size = max(0, int(size_bytes or 0))
    mb = size / (1024 * 1024)
    if mb >= 100:
        return f"{mb:.0f} MB"
    if mb >= 1:
        return f"{mb:.1f} MB"
    kb = size / 1024
    if kb >= 1:
        return f"{kb:.0f} KB"
    return f"{size} B"
