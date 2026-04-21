"""Tests for core.consensus.vertex_client — STUB + LIVE branch coverage."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.consensus import vertex_client
from core.consensus.vertex_client import VertexReceipt


def test_sha256_deterministic():
    a = vertex_client._sha256({"a": 1, "b": 2})
    b = vertex_client._sha256({"b": 2, "a": 1})
    assert a == b


def test_sha256_changes_with_content():
    a = vertex_client._sha256({"a": 1})
    b = vertex_client._sha256({"a": 2})
    assert a != b


def test_broker_host_port_defaults(monkeypatch):
    monkeypatch.setenv("FOXMQ_BROKER_URL", "mqtt://foxmq:1883")
    assert vertex_client._broker_host_port() == ("foxmq", 1883)


def test_use_real_vertex_false(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    assert vertex_client._use_real_vertex() is False


def test_use_real_vertex_true(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    assert vertex_client._use_real_vertex() is True


def test_increment_round_counter_redis_success():
    fake_redis = MagicMock()
    fake_redis.incr.return_value = 42
    with patch("redis.from_url", return_value=fake_redis):
        n = vertex_client._increment_round_counter()
    assert n == 42


def test_increment_round_counter_redis_fail_falls_back():
    with patch("redis.from_url", side_effect=RuntimeError("no redis")):
        n1 = vertex_client._increment_round_counter()
        n2 = vertex_client._increment_round_counter()
    assert n2 == n1 + 1


def test_submit_stub_returns_receipt(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    with patch("redis.from_url", side_effect=RuntimeError("x")):
        receipt = vertex_client.submit_event({"task_id": "t1", "event_type": "task_completed"})
    assert isinstance(receipt, VertexReceipt)
    assert receipt.is_stub is True
    assert receipt.foxmq_timestamp is None
    assert len(receipt.event_hash) == 64
    assert receipt.round >= 1


def test_submit_live_success(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    mock_client = MagicMock()

    def fake_connect(host, port, keepalive):
        mock_client.on_connect(mock_client, None, None, 0, None)

    mock_client.connect.side_effect = fake_connect

    def fake_publish(topic, payload, qos=0, **kw):
        # Trigger on_publish with timestamp user property
        props = MagicMock()
        props.UserProperty = [("timestamp_received", "2026-04-21T18:00:00Z")]
        mock_client.on_publish(mock_client, None, 1, 0, props)
        return MagicMock()

    mock_client.publish.side_effect = fake_publish
    mock_client.loop_start = MagicMock()
    mock_client.loop_stop = MagicMock()
    mock_client.disconnect = MagicMock()

    with patch("paho.mqtt.client.Client", return_value=mock_client), \
         patch("redis.from_url", side_effect=RuntimeError("x")):
        receipt = vertex_client.submit_event({"task_id": "abc", "event_type": "task_completed"})

    assert receipt.is_stub is False
    assert receipt.foxmq_timestamp == "2026-04-21T18:00:00Z"


def test_submit_live_connect_fail_falls_back_to_stub(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    mock_client = MagicMock()
    # Never trigger on_connect → ConnectionError → fallback to stub
    mock_client.connect = MagicMock()
    mock_client.loop_start = MagicMock()
    mock_client.loop_stop = MagicMock()
    mock_client.disconnect = MagicMock()

    with patch("paho.mqtt.client.Client", return_value=mock_client), \
         patch("redis.from_url", side_effect=RuntimeError("x")), \
         patch("time.sleep"):
        receipt = vertex_client.submit_event({"task_id": "y"})

    assert receipt.is_stub is True


def test_submit_live_exception_falls_back(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    with patch("paho.mqtt.client.Client", side_effect=RuntimeError("boom")), \
         patch("redis.from_url", side_effect=RuntimeError("x")):
        receipt = vertex_client.submit_event({"task_id": "y"})
    assert receipt.is_stub is True


def test_vertex_submit_error_is_exception():
    assert issubclass(vertex_client.VertexSubmitError, Exception)


def test_vertex_receipt_dataclass():
    r = VertexReceipt(
        event_hash="a" * 64, round=1, finalised_at="2026-04-21T18:00:00",
        is_stub=True, foxmq_timestamp=None,
    )
    assert r.event_hash == "a" * 64
    assert r.is_stub is True
