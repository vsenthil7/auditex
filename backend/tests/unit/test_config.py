"""Tests for app.config — Settings singleton."""
import importlib

import pytest


def test_settings_defaults_load():
    from app.config import settings
    assert settings.CLAUDE_MODEL
    assert settings.GPT4O_MODEL
    assert settings.ENVIRONMENT
    assert settings.LOG_LEVEL
    assert settings.API_PORT > 0
    assert settings.DATABASE_URL
    assert settings.REDIS_URL
    assert settings.FOXMQ_BROKER_URL
    assert settings.VERTEX_NODE_URL
    assert settings.JWT_SECRET
    assert settings.API_KEY_SALT


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("CLAUDE_MODEL", "claude-3-opus")
    monkeypatch.setenv("API_PORT", "9999")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    # Re-import app.config to pick up new env
    import app.config as cfg
    importlib.reload(cfg)
    assert cfg.settings.CLAUDE_MODEL == "claude-3-opus"
    assert cfg.settings.API_PORT == 9999
    # Reload back so other tests see default
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    importlib.reload(cfg)
