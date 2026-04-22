"""Auditex -- Schema validator (Phase 12: backed by jsonschema==4.23.0).

Thin wrapper around ``jsonschema.Draft202012Validator`` that preserves the
public contract used elsewhere in the codebase::

    validate_payload(schema, payload) -> tuple[bool, list[str]]

Previously this module implemented a tiny home-grown subset of JSONSchema.
It has been replaced with the market-standard ``jsonschema`` library, which
is the same library FastAPI / OpenAPI tooling builds on. The public return
shape is unchanged; error messages now come from ``jsonschema`` but retain
the same "$.path.to.field: <message>" format.
"""
from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema import SchemaError as _JsonSchemaSchemaError


class SchemaError(Exception):
    """Raised when the schema definition itself is malformed.

    Kept as its own class (rather than a re-export of
    ``jsonschema.SchemaError``) so existing call-sites that catch
    ``core.ingestion.schema_validator.SchemaError`` continue to work.
    """


def _format_path(path_parts: list[Any]) -> str:
    """Render a jsonschema error path as our canonical ``$.a.b[0]`` string."""
    out = "$"
    for part in path_parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}"
    return out


def validate_payload(
    schema: dict, payload: Any, path: str = "$"
) -> tuple[bool, list[str]]:
    """Validate ``payload`` against ``schema``.

    Returns ``(ok, errors)`` where ``ok`` is True iff ``errors`` is empty.
    Raises :class:`SchemaError` if the schema itself is malformed (not a
    dict, uses an unknown type keyword, etc).

    The ``path`` parameter is retained for API compatibility with the
    previous home-grown implementation; it is used as the root prefix of
    reported error paths.
    """
    if not isinstance(schema, dict):
        raise SchemaError(f"schema at {path} is not a dict")

    # Validate the schema itself first. This catches malformed schemas
    # (e.g. {"type": "nonsense"}) with a consistent SchemaError rather
    # than surfacing them as ordinary payload-validation failures.
    try:
        Draft202012Validator.check_schema(schema)
    except _JsonSchemaSchemaError as exc:
        raise SchemaError(f"invalid schema at {path}: {exc.message}") from exc

    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
        loc = _format_path(list(err.absolute_path))
        # Ensure the root prefix honours the caller-supplied path (for
        # nested recursive use-cases, the previous implementation prefixed
        # every error with the caller's ``path`` argument).
        if path != "$" and loc.startswith("$"):
            loc = path + loc[1:]
        errors.append(f"{loc}: {err.message}")

    return (len(errors) == 0), errors
