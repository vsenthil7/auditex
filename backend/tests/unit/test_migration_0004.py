"""Tests for migration 0004_add_webhook_tables."""
from __future__ import annotations

import importlib.util
import pathlib
from unittest.mock import patch


def _load():
    p = pathlib.Path("db/migrations/versions/0004_add_webhook_tables.py")
    spec = importlib.util.spec_from_file_location("mig0004", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_metadata():
    m = _load()
    assert m.revision == "0004"
    assert m.down_revision == "0003"


def test_upgrade_creates_two_tables_and_two_indexes():
    m = _load()
    with patch.object(m, "op") as mk_op:
        m.upgrade()
    assert mk_op.create_table.call_count == 2
    tables = [c.args[0] for c in mk_op.create_table.call_args_list]
    assert "webhook_subscriptions" in tables
    assert "webhook_deliveries" in tables
    assert mk_op.create_index.call_count == 2


def test_downgrade_drops_indexes_and_tables():
    m = _load()
    with patch.object(m, "op") as mk_op:
        m.downgrade()
    assert mk_op.drop_index.call_count == 2
    assert mk_op.drop_table.call_count == 2
    tables = [c.args[0] for c in mk_op.drop_table.call_args_list]
    assert "webhook_subscriptions" in tables
    assert "webhook_deliveries" in tables
