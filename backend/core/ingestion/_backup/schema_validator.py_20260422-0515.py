"""Auditex -- Minimal schema validator (Phase 11 Item 10).

Tiny JSONSchema-subset validator with zero external dependencies. Supports
only what Auditex agent payloads need:
  - type: object, array, string, integer, number, boolean, null
  - required: list of keys
  - properties: dict mapping key -> sub-schema
  - items: sub-schema for array elements
  - enum: list of allowed values
  - minLength / maxLength for strings
Returns (ok: bool, errors: list[str]).
"""
from __future__ import annotations

from typing import Any

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


class SchemaError(Exception):
    """Raised when the schema definition itself is malformed."""


def validate_payload(schema: dict, payload: Any, path: str = "$") -> tuple[bool, list[str]]:
    """Recursively validate payload against schema. Returns (ok, errors)."""
    if not isinstance(schema, dict):
        raise SchemaError(f"schema at {path} is not a dict")
    errors: list[str] = []

    # type check
    t = schema.get("type")
    if t is not None:
        if t not in _TYPE_MAP:
            raise SchemaError(f"unknown type {t} at {path}")
        # special: integer check must exclude bool (bool is subclass of int in Python)
        if t == "integer" and isinstance(payload, bool):
            errors.append(f"{path}: expected integer, got boolean")
        elif not isinstance(payload, _TYPE_MAP[t]):
            errors.append(f"{path}: expected {t}, got {type(payload).__name__}")
            return False, errors

    # enum check
    if "enum" in schema and payload not in schema["enum"]:
        errors.append(f"{path}: value {payload!r} not in enum {schema['enum']}")

    # string-specific
    if isinstance(payload, str):
        if "minLength" in schema and len(payload) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(payload) > schema["maxLength"]:
            errors.append(f"{path}: string longer than maxLength {schema['maxLength']}")

    # object-specific
    if isinstance(payload, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in payload:
                errors.append(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        for key, sub_schema in props.items():
            if key in payload:
                ok, sub_errs = validate_payload(sub_schema, payload[key], path=f"{path}.{key}")
                errors.extend(sub_errs)

    # array-specific
    if isinstance(payload, list) and "items" in schema:
        item_schema = schema["items"]
        for i, element in enumerate(payload):
            ok, sub_errs = validate_payload(item_schema, element, path=f"{path}[{i}]")
            errors.extend(sub_errs)

    return (len(errors) == 0), errors
