from core.modules.strategy.engines.simulator.enumerator.live_progress import (
    format_elapsed_seconds,
)


def test_format_elapsed_seconds():
    assert format_elapsed_seconds(12.3) == "12.3s"
    assert format_elapsed_seconds(90) == "1m30s"
    assert format_elapsed_seconds(120) == "2m"
