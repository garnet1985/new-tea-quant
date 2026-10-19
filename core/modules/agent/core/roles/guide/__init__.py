"""介绍者：答产品疑问（wiki）或讲架构（arch）。只读，不写 userspace。"""

from core.modules.agent.core.roles.guide.patterns import is_architecture_question

__all__ = ["is_architecture_question"]
