"""Tag visualization shaping (no DB)."""

from __future__ import annotations

from core.bff.APIs.tag.helpers.tag_visualization import (
    build_entity_rows,
    build_intervals,
    build_snapshots,
    decode_value,
    normalize_point,
    shape_snapshot,
)


def _point(**kwargs):
    base = {
        "entity_id": "000001",
        "as_of": "20240101",
        "start_date": "",
        "end_date": "",
        "tag_name": "market_cap_tier",
        "tag_display_name": "市值",
        "value": "high",
    }
    base.update(kwargs)
    return base


def test_decode_value_unwraps_stored_payload():
    assert decode_value('{"value":"high"}') == "high"
    assert decode_value({"value": {"clusters": {}}}) == {"clusters": {}}
    assert decode_value("mid") == "mid"


def test_normalize_point_reads_columns():
    point = normalize_point(
        {
            "entity_id": "000001",
            "as_of_date": "2024-03-01",
            "start_date": None,
            "end_date": None,
            "json_value": '{"value":"low"}',
            "tag_name": "market_cap_tier",
            "tag_display_name": "市值",
        }
    )
    assert point is not None
    assert point["as_of"] == "20240301"
    assert point["value"] == "low"


def test_intervals_merge_unchanged_runs_until_next_value():
    intervals = build_intervals(
        [
            _point(as_of="20240101", value="high"),
            _point(as_of="20240301", value="high"),
            _point(as_of="20240601", value="low"),
        ],
        "20241231",
    )
    assert [(item["lane"], item["value_label"], item["start"], item["end"]) for item in intervals] == [
        ("市值", "high", "20240101", "20240601"),
        ("市值", "low", "20240601", "20241231"),
    ]


def test_intervals_keep_explicit_span_and_do_not_stretch_it():
    intervals = build_intervals(
        [
            _point(
                as_of="20240101",
                value="high",
                start_date="20240101",
                end_date="20240201",
            ),
            _point(as_of="20240301", value="mid"),
        ],
        "20241231",
    )
    assert [(item["value_label"], item["start"], item["end"]) for item in intervals] == [
        ("high", "20240101", "20240201"),
        ("mid", "20240301", "20241231"),
    ]


def test_intervals_use_definition_lanes_when_multiple_tags():
    intervals = build_intervals(
        [
            _point(as_of="20240101", value="high"),
            _point(
                as_of="20240101",
                tag_name="liquidity",
                tag_display_name="流动性",
                value="thin",
            ),
        ],
        "20240601",
    )
    assert {item["lane"] for item in intervals} == {"市值", "流动性"}
    assert {item["value_label"] for item in intervals} == {"high", "thin"}
    assert {item["end"] for item in intervals} == {"20240601"}


def test_entity_rows_join_current_values():
    rows = build_entity_rows(
        [
            _point(entity_id="000002", as_of="20240102", value="low"),
            _point(entity_id="000001", as_of="20240501", value="high"),
            _point(entity_id="__global__", as_of="20240501", value="easing"),
        ],
        {"000001": "平安银行"},
    )
    assert [row["entity_id"] for row in rows] == ["000001", "000002"]
    assert rows[0]["entity_name"] == "平安银行"
    assert rows[0]["tag_label"] == "市值"
    assert rows[0]["value_detail"] == "high"
    assert rows[1]["entity_name"] == "000002"


def test_entity_rows_keep_the_latest_tag():
    rows = build_entity_rows(
        [
            _point(
                entity_id="000001",
                as_of="20240101",
                tag_name="low_cap",
                tag_display_name="低市值",
                value="8.0亿元",
            ),
            _point(
                entity_id="000001",
                as_of="20240601",
                tag_name="high_cap",
                tag_display_name="高市值",
                value="120.0亿元",
            ),
        ]
    )
    assert rows[0]["tag_label"] == "高市值"
    assert rows[0]["value_detail"] == "120.0亿元"
    assert rows[0]["as_of"] == "20240601"


def test_intervals_hand_off_between_tags():
    intervals = build_intervals(
        [
            _point(
                as_of="20240101",
                tag_name="low_cap",
                tag_display_name="低市值",
                value="8.0亿元",
            ),
            _point(
                as_of="20240601",
                tag_name="high_cap",
                tag_display_name="高市值",
                value="120.0亿元",
            ),
        ],
        "20241231",
    )
    assert [(item["lane"], item["value_label"], item["start"], item["end"]) for item in intervals] == [
        ("低市值", "8.0亿元", "20240101", "20240601"),
        ("高市值", "120.0亿元", "20240601", "20241231"),
    ]


def test_snapshot_categories_from_nested_clusters():
    shaped = shape_snapshot(
        {
            "universe_size": 3,
            "clusters": {
                "长三角": {
                    "count": 2,
                    "provinces": ["上海", "江苏"],
                    "sample_ids": ["600000"],
                    "unmapped": 0,
                },
                "其它": {"count": 1, "provinces": [], "sample_ids": [], "unmapped": 1},
            },
        }
    )
    assert shaped["kind"] == "categories"
    assert shaped["categories"][0]["name"] == "长三角"
    assert shaped["categories"][0]["count"] == 2
    assert "上海" in shaped["categories"][0]["detail"]
    assert shaped["categories"][0]["samples"] == "600000"


def test_snapshots_keep_latest_point_per_definition():
    snapshots = build_snapshots(
        [
            _point(as_of="20240101", value="low"),
            _point(as_of="20240601", value="high"),
        ]
    )
    assert len(snapshots) == 1
    assert snapshots[0]["kind"] == "scalar"
    assert snapshots[0]["scalar"] == "high"
    assert snapshots[0]["as_of"] == "20240601"
