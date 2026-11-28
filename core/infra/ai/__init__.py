"""AI 通道（``infra.ai``）— 本机供应商连接、密钥与裸补全。

公开门面::

    from core.infra.ai import AiChannel

跨模块契约::

    from core.infra.ai.contracts import AiError, CompleteResult, ProviderInfo

官网会员补全见 ``modules.ntq_external.ai.member_channel``（经 ``AiChannel.complete_http``）。
"""

from .ai_channel import AiChannel

__all__ = ["AiChannel"]
