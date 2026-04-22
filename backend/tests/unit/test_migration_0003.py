"""Tests for migration 0003_add_dlq_entries."""
from __future__ import annotations

import importlib.util
import pathlib
from unittest.mock import MagicMock, patch


def _load_migration():
    p = pathlib.Path("db/migrations/versions/0003_add_dlq_entries.py")
    spec = importlib.util.spec_from_file_location("mig0003", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_metadata():
    m = _load_migration()
    assert m.revision == "0003"
    assert m.down_revision == "0002"


def test_migration_upgrade_calls_create_table_and_indexes():
    m = _load_migration()
    with patch.object(m, "op") as mk_op:
        m.upgrade()
    mk_op.create_table.assert_called_once()
    args = mk_op.create_table.call_args.args
    assert args[0] == "dlq_entries"
    assert mk_op.create_index.call_count == 2


def test_migration_downgrade_drops_indexes_and_table():
    m = _load_migration()
    with patch.object(m, "op") as mk_op:
        m.downgrade()
    assert mk_op.drop_index.call_count == 2
    mk_op.drop_table.assert_called_once_with("dlq_entries")
