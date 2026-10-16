"""一次 renew 的进度。由引擎写出，handler 不自己拼日志。"""

from __future__ import annotations


class SyncProgress:
    """终端和运行日志共用的进度行。"""

    def __init__(self, source: str):
        self.source = str(source or "data_source")

    def bundles(self, done: int, total: int, saved: int, failed: int = 0) -> None:
        line = f"抓取 {done}/{total}，已写入 {saved} 行"
        if failed:
            line += f"，失败 {failed}"
        print(f"[{self.source}] {line}", flush=True)
        self._publish(done=done, total=total, saved=saved, label=line)

    def tables(self, total: int) -> None:
        label = f"开始同步，共 {total} 张表"
        print(f"[{self.source}] {label}", flush=True)
        self._publish(done=0, total=total, saved=0, label=label)

    def table(self, index: int, total: int, table: str, label: str) -> None:
        text = f"第 {index}/{total} 张 {table}（{label}）"
        print(f"[{self.source}] {text}", flush=True)
        self._publish(done=index, total=total, saved=None, label=text)

    def page(self, table: str, label: str, page: int, saved: int, total: int | None = None) -> None:
        line = f"同步 {table}（{label}）正在读取第 {page} 页，已写入 {saved} 行"
        if total is not None and total > 0:
            line += f"，{_percent_text(saved, total)}"
        print(f"[{self.source}] {line}", flush=True)
        done = saved if total is not None and total > 0 else None
        whole = total if total is not None and total > 0 else None
        self._publish(done=done, total=whole, saved=saved, label=line)

    def _publish(
        self,
        *,
        done: int | None,
        total: int | None,
        saved: int | None,
        label: str,
    ) -> None:
        from core.modules.data_source.core.service.run_status import publish_progress

        publish_progress(self.source, done=done, total=total, saved=saved, label=label)

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


__all__ = ["SyncProgress"]
