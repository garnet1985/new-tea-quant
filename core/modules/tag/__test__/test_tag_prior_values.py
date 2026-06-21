from core.modules.tag.engines.shared.staging.prior_values import (
    encode_tag_json_value,
    load_latest_tag_value_json,
    parse_tag_value_bool,
    parse_tag_value_scalar,
)


def test_encode_tag_json_value_scalar():
    assert encode_tag_json_value({"value": "high"}) == '{"value":"high"}'


def test_encode_tag_json_value_strips_tag_name():
    assert encode_tag_json_value({"tag_name": "t1", "value": "picked"}) == '{"value":"picked"}'


def test_parse_tag_value_scalar_from_encoded_json():
    assert parse_tag_value_scalar('{"value":"high"}') == "high"


def test_load_latest_from_inject_prior():
    payload = {
        "_inject": {
            "prior_tag_values": {"2": '{"value": true}'},
        }
    }
    raw = load_latest_tag_value_json(
        payload,
        None,
        entity_id="000001.SZ",
        tag_definition_id=2,
    )
    assert raw == '{"value": true}'
    assert parse_tag_value_bool(raw) is True


def test_load_latest_without_inject_returns_none_without_service():
    assert (
        load_latest_tag_value_json({}, None, entity_id="x", tag_definition_id=1) is None
    )
