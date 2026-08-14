"""Argparse helpers that print only the curated help_text template."""

from __future__ import annotations

import argparse


class HelpTextOnlyParser(argparse.ArgumentParser):
    """``-h`` / ``print_help`` 只输出 help_text 模版，不拼 argparse 自动帮助。"""

    def __init__(self, *args, help_text: str, **kwargs) -> None:
        self._help_text = help_text.strip()
        kwargs.pop("formatter_class", None)
        kwargs.pop("epilog", None)
        kwargs.pop("description", None)
        super().__init__(*args, **kwargs)

    def format_help(self) -> str:
        return self._help_text + "\n"
