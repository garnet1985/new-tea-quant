"""ASCII 标题块：h1 / h2 / h3 / h4。"""

from __future__ import annotations

from typing import Optional, TextIO

from core.infra.cmd_layout.shared.display import display_width
from core.infra.cmd_layout.shared.stream import StreamWriter


class Title:
    """终端报告标题层级。"""

    DEFAULT_CHAR = "*"
    DEFAULT_BANNER_PAD = 16
    DEFAULT_H2_CHAR = "="
    DEFAULT_H2_MIN_WIDTH = 24
    DEFAULT_H3_CHAR = "-"
    DEFAULT_H4_PREFIX = "###"

    @staticmethod
    def display_width(text: str) -> int:
        """兼容旧调用；实现见 ``shared.display``。"""
        return display_width(text)

    @classmethod
    def _star_box(
        cls,
        text: str,
        *,
        char: str = DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
    ) -> str:
        """星号框主体（供 h1 使用）。"""
        body = str(text)
        rule_char = (char or cls.DEFAULT_CHAR)[:1] or "*"
        body_width = display_width(body)
        if width is not None:
            rule_width = max(1, int(width))
        else:
            side_pad = cls.DEFAULT_BANNER_PAD if pad is None else max(0, int(pad))
            rule_width = max(1, body_width + side_pad)
        rule = rule_char * rule_width
        if center and body_width < rule_width:
            gap = rule_width - body_width
            left = gap // 2
            right = gap - left
            body = f"{' ' * left}{body}{' ' * right}"
        return f"{rule}\n{body}\n{rule}"

    @classmethod
    def h1(
        cls,
        text: str,
        *,
        char: str = DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
    ) -> str:
        """报告总标题：前空行 + 星号框。"""
        return "\n" + cls._star_box(
            text, char=char, width=width, center=center, pad=pad
        )

    @classmethod
    def h2(
        cls,
        text: str,
        *,
        char: str = DEFAULT_H2_CHAR,
        min_width: int = DEFAULT_H2_MIN_WIDTH,
    ) -> str:
        """大节：前空行 + 正文 + 等号下划线。"""
        body = str(text).strip()
        rule_char = (char or cls.DEFAULT_H2_CHAR)[:1] or "="
        rule_width = max(display_width(body), max(1, int(min_width)))
        return f"\n{body}\n{rule_char * rule_width}"

    @classmethod
    def h3(
        cls,
        text: str,
        *,
        char: str = DEFAULT_H3_CHAR,
    ) -> str:
        """小节：前空行 + ``--- heading ---``。"""
        rule_char = (char or cls.DEFAULT_H3_CHAR)[:1] or "-"
        body = str(text).strip()
        deco = rule_char * 3
        return f"\n{deco} {body} {deco}"

    @classmethod
    def h4(
        cls,
        text: str,
        *,
        prefix: str = DEFAULT_H4_PREFIX,
    ) -> str:
        """细节标题：前空行 + ``### text``。"""
        mark = str(prefix or cls.DEFAULT_H4_PREFIX).strip() or cls.DEFAULT_H4_PREFIX
        body = str(text).strip()
        return f"\n{mark} {body}"

    @classmethod
    def print_h1(
        cls,
        text: str,
        *,
        char: str = DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.h1(text, char=char, width=width, center=center, pad=pad)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_h2(
        cls,
        text: str,
        *,
        char: str = DEFAULT_H2_CHAR,
        min_width: int = DEFAULT_H2_MIN_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.h2(text, char=char, min_width=min_width)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_h3(
        cls,
        text: str,
        *,
        char: str = DEFAULT_H3_CHAR,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.h3(text, char=char)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_h4(
        cls,
        text: str,
        *,
        prefix: str = DEFAULT_H4_PREFIX,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.h4(text, prefix=prefix)
        StreamWriter.write(out, stream=stream)
        return out


class TitleNamespace:
    """CmdLayout.title 命名空间。"""

    @staticmethod
    def h1(
        text: str,
        *,
        char: str = Title.DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
    ) -> str:
        return Title.h1(text, char=char, width=width, center=center, pad=pad)

    @staticmethod
    def h2(
        text: str,
        *,
        char: str = Title.DEFAULT_H2_CHAR,
        min_width: int = Title.DEFAULT_H2_MIN_WIDTH,
    ) -> str:
        return Title.h2(text, char=char, min_width=min_width)

    @staticmethod
    def h3(
        text: str,
        *,
        char: str = Title.DEFAULT_H3_CHAR,
    ) -> str:
        return Title.h3(text, char=char)

    @staticmethod
    def h4(
        text: str,
        *,
        prefix: str = Title.DEFAULT_H4_PREFIX,
    ) -> str:
        return Title.h4(text, prefix=prefix)

    @staticmethod
    def print_h1(
        text: str,
        *,
        char: str = Title.DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_h1(
            text, char=char, width=width, center=center, pad=pad, stream=stream
        )

    @staticmethod
    def print_h2(
        text: str,
        *,
        char: str = Title.DEFAULT_H2_CHAR,
        min_width: int = Title.DEFAULT_H2_MIN_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_h2(
            text, char=char, min_width=min_width, stream=stream
        )

    @staticmethod
    def print_h3(
        text: str,
        *,
        char: str = Title.DEFAULT_H3_CHAR,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_h3(text, char=char, stream=stream)

    @staticmethod
    def print_h4(
        text: str,
        *,
        prefix: str = Title.DEFAULT_H4_PREFIX,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_h4(text, prefix=prefix, stream=stream)
