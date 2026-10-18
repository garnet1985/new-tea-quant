"""一次 renew 里，当前数据源的子步骤。终端仍打一行给人看，数字写进进度文件。"""

from __future__ import annotations

_LEAF = ""


def bind_renew_leaf(node_id: str) -> None:
    """当前正在抓取的进度节点。空字符串表示先不写文件。"""
    global _LEAF
    _LEAF = str(node_id or "")


def tick_renew_leaf(done: int, total: int, *, source: str, detail: str) -> None:
    """有当前节点时更新计数。打印仍由调用方负责。"""
    if not _LEAF:
        return
    from core.infra.progress import Progress

    Progress.tick(_LEAF, done, total, source=source, detail=detail, log=False)


class SyncProgress:
    """当前数据源的子步骤。总步骤由调度器写入。"""

    def __init__(self, source: str):
        self.source = str(source or "data_source")

    def bundles(self, done: int, total: int, saved: int, failed: int = 0) -> None:
        line = f"抓取 {done}/{total}，已写入 {saved} 行"
        if failed:
            line += f"，失败 {failed}"
        print(f"[{self.source}] {line}", flush=True)
        tick_renew_leaf(done, total, source=self.source, detail=line)

    def tables(self, total: int) -> None:
        label = f"开始同步，共 {total} 张表"
        print(f"[{self.source}] {label}", flush=True)
        tick_renew_leaf(0, total, source=self.source, detail=label)

    def table(self, index: int, total: int, table: str, label: str) -> None:
        text = f"第 {index}/{total} 张 {table}（{label}）"
        print(f"[{self.source}] {text}", flush=True)
        tick_renew_leaf(index, total, source=self.source, detail=text)

    def page(self, table: str, label: str, page: int, saved: int, total: int | None = None) -> None:
        line = f"同步 {table}（{label}）正在读取第 {page} 页，已写入 {saved} 行"
        if total is not None and total > 0:
            line += f"，{_percent_text(saved, total)}"
            tick_renew_leaf(saved, total, source=self.source, detail=line)
        print(f"[{self.source}] {line}", flush=True)

    def table_done(self, table: str, label: str, saved: int, seconds: float) -> None:
        from core.modules.data_source.core.base_class.base_handler import format_run_seconds

        print(
            f"[{self.source}] 同步完成 {table}（{label}）写入 {saved} 行，耗时 {format_run_seconds(seconds)}",
            flush=True,
        )


def _percent_text(saved: int, total: int) -> str:
    pct = saved * 100.0 / total
    if pct >= 10:
        return f"{min(100, int(pct))}%"
    text = f"{pct:.1f}".rstrip("0").rstrip(".")
    return f"{text}%"


__all__ = ["SyncProgress", "bind_renew_leaf", "tick_renew_leaf"]
