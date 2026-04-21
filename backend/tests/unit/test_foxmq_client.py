"""Tests for core.consensus.foxmq_client — stub + live branch coverage.

We don't need a real broker. We mock paho-mqtt and socket to drive both
branches (success, fail-to-connect, publish error, socket-reachable).
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from core.consensus import foxmq_client


def test_use_real_vertex_false_by_default(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    assert foxmq_client._use_real_vertex() is False


def test_use_real_vertex_true(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    assert foxmq_client._use_real_vertex() is True


def test_broker_url_defaults(monkeypatch):
    monkeypatch.setenv("FOXMQ_BROKER_URL", "mqtt://foxmq:1883")
    host, port = foxmq_client._broker_url()
    assert host == "foxmq"
    assert port == 1883


def test_broker_url_mqtts(monkeypatch):
    monkeypatch.setenv("FOXMQ_BROKER_URL", "mqtts://broker:8883")
    host, port = foxmq_client._broker_url()
    assert host == "broker"
    assert port == 8883


def test_broker_url_no_port(monkeypatch):
    monkeypatch.setenv("FOXMQ_BROKER_URL", "mqtt://foxmq")
    host, port = foxmq_client._broker_url()
    assert host == "foxmq"
    assert port == 1883


def test_publish_stub_returns_true():
    ok = foxmq_client._publish_stub({"event_type": "task_completed", "task_id": "abc"})
    assert ok is True


def test_publish_event_stub_mode(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    assert foxmq_client.publish_event({"task_id": "x", "event_type": "y"}) is True


def test_publish_event_live_mode_success(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    mock_client = MagicMock()

    def fake_connect(host, port, keepalive):
        # Immediately fire the on_connect callback with success
        mock_client.on_connect(mock_client, None, None, 0, None)

    mock_client.connect.side_effect = fake_connect
    mock_client.loop_start = MagicMock()

    def fake_publish(topic, payload, qos=0, **kw):
        mock_client.on_publish(mock_client, None, 1, 0, None)
        return MagicMock()

    mock_client.publish.side_effect = fake_publish
    mock_client.loop_stop = MagicMock()
    mock_client.disconnect = MagicMock()

    with patch("paho.mqtt.client.Client", return_value=mock_client):
        # Also patch CallbackAPIVersion and MQTTv5 just in case
        with patch("paho.mqtt.client.CallbackAPIVersion", MagicMock()):
            ok = foxmq_client.publish_event(
                {"task_id": "abc12345", "event_type": "task_completed"}
            )
    assert ok is True


def test_publish_event_live_connect_fail_falls_back(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    mock_client = MagicMock()
    # Never trigger on_connect success → connected stays False → fallback path
    mock_client.connect = MagicMock()
    mock_client.loop_start = MagicMock()
    mock_client.loop_stop = MagicMock()
    mock_client.disconnect = MagicMock()

    with patch("paho.mqtt.client.Client", return_value=mock_client), \
         patch("time.sleep"):
        ok = foxmq_client.publish_event({"task_id": "x", "event_type": "y"})
    assert ok is True  # fallback to stub always returns True


def test_publish_event_live_exception_falls_back(monkeypatch):
    """Exception inside the try-block of _publish_real must be caught and
    the stub fallback must then still return True. We trigger this by making
    client.connect() raise after Client() succeeds."""
    monkeypatch.setenv("USE_REAL_VERTEX", "true")

    mock_client = MagicMock()
    mock_client.connect = MagicMock(side_effect=RuntimeError("connect boom"))
    # loop_stop + disconnect should still be called in the cleanup path
    mock_client.loop_stop = MagicMock()
    mock_client.disconnect = MagicMock()
    mock_client.loop_start = MagicMock()

    with patch("paho.mqtt.client.Client", return_value=mock_client), \
         patch("paho.mqtt.client.CallbackAPIVersion", MagicMock()):
        ok = foxmq_client.publish_event({"task_id": "x", "event_type": "y"})
    assert ok is True  # fallback to stub always returns True


def test_publish_event_live_cleanup_exception_swallowed(monkeypatch):
    """Covers the inner try/except around loop_stop+disconnect in the
    cleanup path (lines 117-122)."""
    monkeypatch.setenv("USE_REAL_VERTEX", "true")

    mock_client = MagicMock()
    mock_client.connect = MagicMock(side_effect=RuntimeError("connect boom"))
    mock_client.loop_stop = MagicMock(side_effect=RuntimeError("cleanup boom"))
    mock_client.disconnect = MagicMock()
    mock_client.loop_start = MagicMock()

    with patch("paho.mqtt.client.Client", return_value=mock_client), \
         patch("paho.mqtt.client.CallbackAPIVersion", MagicMock()):
        ok = foxmq_client.publish_event({"task_id": "x", "event_type": "y"})
    assert ok is True


def test_publish_event_live_connect_nonzero_reason_code(monkeypatch):
    """Covers the on_connect `reason_code != 0` branch (line 64)."""
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    mock_client = MagicMock()

    def fake_connect(host, port, keepalive):
        # Fire on_connect with a FAILED reason code
        mock_client.on_connect(mock_client, None, None, 5, None)

    mock_client.connect.side_effect = fake_connect
    mock_client.loop_start = MagicMock()
    mock_client.loop_stop = MagicMock()
    mock_client.disconnect = MagicMock()

    with patch("paho.mqtt.client.Client", return_value=mock_client), \
         patch("paho.mqtt.client.CallbackAPIVersion", MagicMock()), \
         patch("time.sleep"):
        ok = foxmq_client.publish_event({"task_id": "abc", "event_type": "y"})
    assert ok is True  # falls back to stub


def test_publish_event_live_publish_ack_timeout(monkeypatch):
    """Covers line 102: connected OK, publish called, but on_publish callback
    never fires within the deadline. The while-loop exits on time.time()."""
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    mock_client = MagicMock()

    def fake_connect(host, port, keepalive):
        mock_client.on_connect(mock_client, None, None, 0, None)  # connected OK

    mock_client.connect.side_effect = fake_connect
    # publish() is called but on_publish is NEVER fired
    mock_client.publish.return_value = MagicMock()
    mock_client.loop_start = MagicMock()
    mock_client.loop_stop = MagicMock()
    mock_client.disconnect = MagicMock()

    # Fake time so the deadline exit fires immediately on the publish wait loop
    # First few calls: small values for connect loop + first deadline computation
    # Later calls: huge values to force deadline exit
    fake_times = iter([0.0, 0.1, 0.2, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    with patch("paho.mqtt.client.Client", return_value=mock_client), \
         patch("paho.mqtt.client.CallbackAPIVersion", MagicMock()), \
         patch("time.sleep"), \
         patch("time.time", side_effect=lambda: next(fake_times)):
        ok = foxmq_client.publish_event({"task_id": "abc", "event_type": "y"})
    assert ok is True  # publish is considered a success even without ack


def test_is_live_stub_mode(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    assert foxmq_client.is_live() is False


def test_is_live_real_mode_socket_success(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    fake_sock = MagicMock()
    with patch("socket.create_connection", return_value=fake_sock):
        assert foxmq_client.is_live() is True


def test_is_live_real_mode_socket_fails(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    with patch("socket.create_connection", side_effect=OSError("refused")):
        assert foxmq_client.is_live() is False


def test_foxmq_publish_error_is_exception():
    assert issubclass(foxmq_client.FoxMQPublishError, Exception)
