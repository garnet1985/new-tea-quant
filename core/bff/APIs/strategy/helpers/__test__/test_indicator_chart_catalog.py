"""Tests for shared indicator → chart render catalog."""

from core.bff.APIs.strategy.helpers.indicator_chart_catalog import (
    resolve_indicator_render,
    resolve_indicator_render_from_column,
)


def test_rsi_is_oscillator_fixed_scale():
    meta = resolve_indicator_render("rsi", field_key="rsi14", params={"length": 14})
    assert meta["panel"] == "oscillator"
    assert meta["kind"] == "line"
    assert meta["y_axis"]["min"] == 0
    assert meta["y_axis"]["max"] == 100


def test_macd_hist_is_signed_bar_same_group():
    params = {"fast": 12, "slow": 26, "signal": 9}
    dif = resolve_indicator_render(
        "macd", sub_key="MACD_12_26_9", field_key="macd_macd_12_26_9", params=params
    )
    hist = resolve_indicator_render(
        "macd", sub_key="MACDh_12_26_9", field_key="macd_macdh_12_26_9", params=params
    )
    assert dif["panel"] == "macd"
    assert dif["kind"] == "line"
    assert hist["panel"] == "macd"
    assert hist["kind"] == "bar"
    assert hist["signed"] is True
    assert dif["pane_group"] == hist["pane_group"]


def test_bbands_split_overlay_and_oscillator():
    mid = resolve_indicator_render("bbands", sub_key="BBM_20_2.0", params={"length": 20})
    pct = resolve_indicator_render("bbands", sub_key="BBP_20_2.0", params={"length": 20})
    bw = resolve_indicator_render("bbands", sub_key="BBB_20_2.0", params={"length": 20})
    assert mid["panel"] == "overlay"
    assert pct["panel"] == "oscillator"
    assert pct["pane_group"] == "osc:bbp"
    assert pct["y_axis"] == {"scale": True}
    assert bw["pane_group"] == "osc:bbb"


def test_obv_gets_own_oscillator_pane():
    meta = resolve_indicator_render_from_column("obv")
    assert meta["panel"] == "oscillator"
    assert meta["pane_group"] == "volind:obv"


def test_sma_overlay():
    meta = resolve_indicator_render("sma", field_key="sma20", params={"length": 20})
    assert meta["panel"] == "overlay"
    assert meta["kind"] == "line"


def test_supertrend_aux_columns_skipped():
    from core.bff.APIs.strategy.helpers.indicator_chart_catalog import (
        should_skip_chart_series,
    )

    assert should_skip_chart_series(
        name="supertrend", sub_key="SUPERTd_10_3.0"
    )
    assert should_skip_chart_series(
        name="supertrend", sub_key="SUPERTl_10_3.0"
    )
    assert should_skip_chart_series(
        name="supertrend", sub_key="SUPERTs_10_3.0"
    )
    assert not should_skip_chart_series(
        name="supertrend", sub_key="SUPERT_10_3.0"
    )
    assert should_skip_chart_series(field_key="SUPERTd_10_3.0")
    assert not should_skip_chart_series(field_key="SUPERT_10_3.0")


def test_psar_aux_columns_skipped_keep_dots():
    from core.bff.APIs.strategy.helpers.indicator_chart_catalog import (
        should_skip_chart_series,
    )

    assert should_skip_chart_series(name="psar", sub_key="PSARaf_0.02_0.2")
    assert should_skip_chart_series(name="psar", sub_key="PSARr_0.02_0.2")
    assert not should_skip_chart_series(name="psar", sub_key="PSARl_0.02_0.2")
    assert not should_skip_chart_series(name="psar", sub_key="PSARs_0.02_0.2")


def test_supert_column_maps_to_supertrend_overlay():
    meta = resolve_indicator_render_from_column("SUPERT_10_3.0")
    assert meta["panel"] == "overlay"


def test_macd_labels_are_short():
    from core.bff.APIs.strategy.helpers.indicator_chart_catalog import (
        format_indicator_label,
    )

    assert (
        format_indicator_label("macd", sub_key="MACDh_12_26_9", params={"fast": 12})
        == "MACD HIST"
    )
    assert (
        format_indicator_label("macd", sub_key="MACD_12_26_9", params={"fast": 12})
        == "MACD DIF"
    )
    assert format_indicator_label("rsi", params={"length": 14}) == "RSI(14)"
