"""进度门面。调用方从 core.infra.progress 导入。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from core.infra.progress.contracts import ProgressNode
from core.infra.progress.core import channel_store as _channel
from core.infra.progress.core import store as _store


class _Types:
    Node = ProgressNode


class _ChannelNamespace:
    """频道化 job 快照（与树形节点进度互补；无业务 channel 名）。"""

    @staticmethod
    def path(channel: str, file_key: str) -> Path:
        """``.../progress/{channel}/{file_key}.json``。"""
        return _channel.build_path(channel, file_key)

    @staticmethod
    def write(channel: str, file_key: str, payload: Dict[str, Any]) -> Path:
        """原子写入快照；自动补 ``updated_at``。"""
        return _channel.write(channel, file_key, payload)

    @staticmethod
    def read(channel: str, file_key: str) -> Optional[Dict[str, Any]]:
        """读取快照；不存在或损坏则 ``None``。"""
        return _channel.read(channel, file_key)

    @staticmethod
    def clear(channel: str, file_key: str) -> None:
        """删除快照文件（若存在）。"""
        _channel.clear(channel, file_key)


class Progress:
    """按节点 id 更新进度文件。没有实例。"""

    types = _Types
    channel = _ChannelNamespace()

    @staticmethod
    def start(
        node_id: str,
        *,
        job: str = "",
        label: str = "",
        weight: float = 1,
        steps: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> None:
        """创建或覆盖一棵进度树。子节点在 steps 里，格式与根节点相同。"""
        _store.start(node_id, job=job, label=label, weight=weight, steps=steps)

    @staticmethod
    def tick(
        node_id: str,
        done: int,
        total: int,
        *,
        source: Optional[str] = None,
        label: Optional[str] = None,
        detail: Optional[str] = None,
        log: bool = True,
    ) -> None:
        """更新一个叶子节点。调用一次，文件改一次。log 为真时打一行日志。"""
        _store.tick(
            node_id,
            done,
            total,
            source=source,
            label=label,
            detail=detail,
            log=log,
        )

    @staticmethod
    def finish(node_id: str) -> None:
        """把这个节点标成完成。"""
        _store.finish(node_id)

    @staticmethod
    def fail(node_id: str, detail: str = "") -> None:
        """把这个节点标成失败。"""
        _store.fail(node_id, detail)

    @staticmethod
    def cancel(node_id: str, detail: str = "") -> None:
        """把这个节点标成取消。"""
        _store.cancel(node_id, detail)

    @staticmethod
    def pause(node_id: str) -> None:
        """暂停这个节点。"""
        _store.pause(node_id)

    @staticmethod
    def resume(node_id: str) -> None:
        """恢复这个节点。"""
        _store.resume(node_id)

    @staticmethod
    def clear(node_id: str) -> None:
        """删除包含该节点的根文件。"""
        _store.clear(node_id)

    @staticmethod
    def read(node_id: str) -> Optional[dict]:
        """读取包含该节点的整份根文件。没有则返回 None。"""
        return _store.read(node_id)

    @staticmethod
    def latest(job: str) -> Optional[dict]:
        """同一个 job 里最新的一份根文件。没有则返回 None。"""
        return _store.latest(job)

    @staticmethod
    def drain() -> None:
        """把尚未落盘的进度快照立刻写盘（安装下载等子进程轮询前可主动 flush）。"""
        _store.drain()

    @staticmethod
    def reset_for_tests() -> None:
        """清空内存索引与 flush 状态。仅单测使用；生产勿调用。"""
        _store.reset()


__all__ = ["Progress"]
