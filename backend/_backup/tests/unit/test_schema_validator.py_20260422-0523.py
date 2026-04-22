"""Tests for core.ingestion.schema_validator."""
from __future__ import annotations

import pytest

from core.ingestion.schema_validator import SchemaError, validate_payload


def test_type_object_ok():
    ok, errs = validate_payload({"type": "object"}, {})
    assert ok is True and errs == []


def test_type_object_mismatch():
    ok, errs = validate_payload({"type": "object"}, [1, 2])
    assert ok is False and len(errs) == 1


def test_type_string_ok():
    ok, _ = validate_payload({"type": "string"}, "hi")
    assert ok is True


def test_type_integer_rejects_bool():
    ok, errs = validate_payload({"type": "integer"}, True)
    assert ok is False
    assert any("boolean" in e for e in errs)


def test_type_number_accepts_int_and_float():
    assert validate_payload({"type": "number"}, 1)[0]
    assert validate_payload({"type": "number"}, 1.5)[0]


def test_type_null_accepts_none():
    assert validate_payload({"type": "null"}, None)[0]


def test_type_array_ok():
    assert validate_payload({"type": "array"}, [])[0]


def test_unknown_type_raises_schema_error():
    with pytest.raises(SchemaError):
        validate_payload({"type": "nonsense"}, 1)


def test_schema_not_dict_raises():
    with pytest.raises(SchemaError):
        validate_payload("not a schema", {})


def test_enum_accept_and_reject():
    schema = {"enum": ["a", "b"]}
    assert validate_payload(schema, "a")[0]
    ok, errs = validate_payload(schema, "c")
    assert not ok and len(errs) == 1


def test_string_min_length():
    s = {"type": "string", "minLength": 3}
    assert validate_payload(s, "abc")[0]
    ok, _ = validate_payload(s, "ab")
    assert not ok


def test_string_max_length():
    s = {"type": "string", "maxLength": 3}
    assert validate_payload(s, "ab")[0]
    ok, _ = validate_payload(s, "abcd")
    assert not ok


def test_required_key_missing():
    schema = {"type": "object", "required": ["name"]}
    ok, errs = validate_payload(schema, {})
    assert not ok and any("name" in e for e in errs)


def test_properties_nested_validation():
    schema = {
        "type": "object",
        "properties": {"age": {"type": "integer"}, "name": {"type": "string"}},
        "required": ["age"],
    }
    assert validate_payload(schema, {"age": 5, "name": "a"})[0]
    ok, _ = validate_payload(schema, {"age": "five", "name": "a"})
    assert not ok


def test_array_items_validation():
    schema = {"type": "array", "items": {"type": "integer"}}
    assert validate_payload(schema, [1, 2, 3])[0]
    ok, errs = validate_payload(schema, [1, "two", 3])
    assert not ok and any("[1]" in e for e in errs)
