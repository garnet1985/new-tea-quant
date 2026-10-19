"""介绍者内部：架构问答 vs 一般产品疑问。"""

from __future__ import annotations

import re

ARCHITECTURE_RE = re.compile(
    r"("
    r"架构|原理|源码|设计哲学|模块(结构|划分|职责)|"
    r"框架设计|数据流|目录结构|目录分层|"
    r"userspace.?隔离|core/|"
    r"回测四步.{0,8}(原理|设计|为什么)|"
    r"为什么.{0,12}(拆成|分层|userspace)|"
    r"分层.{0,8}(设计|怎么|如何)"
    r")",
    re.IGNORECASE,
)


def is_architecture_question(text: str) -> bool:
    raw = str(text or "").strip()
    return bool(raw and ARCHITECTURE_RE.search(raw))
