"""Tests for migration 0004_add_webhook_tables."""
from __future__ import annotations

import importlib.util
import pathlib
from unittest.mock import patch


def _load():
    p = pathlib.Path("db/migrations/versions/0004_add_webhook_tables.py")
    spec = importlib.util.spec_from_file_location("mig0004", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_migration_metadata():
    m = _load()
    assert m.revision == "0004"
    assert m.down_revision == "0003"


def test_migration_upgrade_creates_both_tables_and_indexes():
    m = _load()
    with patch.object(m, "op") as mk_op:
        m.upgrade()
    assert mk_op.create_table.call_count == 2
    table_names = [c.args[0] for c in mk_op.create_table.call_args_list]
    assert "webhook_subscriptions" in table_names
    assert "webhook_deliveries" in table_names
    assert mk_op.create_index.call_count == 2


def test_migration_downgrade_drops_indexes_and_tables():
    m = _load()
    with patch.object(m, "op") as mk_op:
        m.downgrade()
    assert mk_op.drop_index.call_count == 2
    assert mk_op.drop_table.call_count == 2
    dropped = [c.args[0] for c in mk_op.drop_table.call_args_list]
    assert "webhook_deliveries" in dropped
    assert "webhook_subscriptions" in dropped
