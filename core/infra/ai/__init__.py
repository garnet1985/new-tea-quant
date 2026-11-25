"""AI 通道（``infra.ai``）— 连接、密钥与裸补全。

公开门面::

    from core.infra.ai import AiChannel

跨模块契约::

    from core.infra.ai.contracts import AiError, CompleteResult, ProviderInfo
"""

from .ai_channel import AiChannel

__all__ = ["AiChannel"]
