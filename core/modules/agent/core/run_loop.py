"""运行循环。模型通道尚未接通，门面不导出本类。

一轮步骤：

1. 组系统提示、工具清单、本机运行记录摘要
2. 经 modules.assistant 的公开入口请求模型（带工具表的补全尚未提供）
3. 回复是人话时，写入运行记录并返回
4. 回复是调用单时，用写入准则校验参数，再执行已实现的工具
5. 把工具摘要送回模型，重复，直到人话或次数上限
"""

from __future__ import annotations

from core.modules.agent.contracts import AgentError


class RunLoop:
    """模型点名与本机执行的循环。"""

    def run(self, content: str) -> str:
        text = str(content or "").strip()
        if not text:
            raise AgentError("消息不能为空")
        raise AgentError("模型通道尚未接通")
