"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from isoproxy.config import ProxyConfig


def test_valid_config_loads(monkeypatch):
    """Test that valid configuration loads successfully."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.anthropic.com")
    monkeypatch.setenv("PROXY_API_KEY", "sk-ant-test123")

    config = ProxyConfig()

    assert config.upstream_base == "https://api.anthropic.com"
    assert config.api_key == "sk-ant-test123"
    assert config.timeout == 30  # Default
    assert config.host == "127.0.0.1"  # Default
    assert config.port == 9000  # Default
    assert config.default_model is None  # Default


def test_missing_upstream_base_raises_error(monkeypatch):
    """Test that missing PROXY_UPSTREAM_BASE raises error."""
    monkeypatch.setenv("PROXY_API_KEY", "sk-ant-test123")

    with pytest.raises(ValidationError):
        ProxyConfig()


def test_missing_api_key_raises_error(monkeypatch):
    """Test that missing PROXY_API_KEY raises error."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.anthropic.com")

    with pytest.raises(ValidationError):
        ProxyConfig()


def test_invalid_upstream_url_raises_error(monkeypatch):
    """Test that invalid upstream URL raises error."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "not-a-url")
    monkeypatch.setenv("PROXY_API_KEY", "sk-ant-test123")

    with pytest.raises(ValidationError):
        ProxyConfig()


def test_placeholder_api_key_raises_error(monkeypatch):
    """Test that placeholder API keys are rejected."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.anthropic.com")
    monkeypatch.setenv("PROXY_API_KEY", "dummy")

    with pytest.raises(ValidationError):
        ProxyConfig()


def test_trailing_slash_removed_from_upstream_base(monkeypatch):
    """Test that trailing slashes are removed from upstream_base."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.anthropic.com/")
    monkeypatch.setenv("PROXY_API_KEY", "sk-ant-test123")

    config = ProxyConfig()

    assert config.upstream_base == "https://api.anthropic.com"


def test_upstream_url_property_constructs_correct_path(monkeypatch):
    """Test that upstream_url property constructs the correct path."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.test.com")
    monkeypatch.setenv("PROXY_API_KEY", "sk-ant-test123")

    config = ProxyConfig()

    assert config.upstream_url == "https://api.test.com/v1/messages"


def test_optional_config_values_applied(monkeypatch):
    """Test that optional configuration values are applied correctly."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.test.com")
    monkeypatch.setenv("PROXY_API_KEY", "sk-ant-test123")
    monkeypatch.setenv("PROXY_DEFAULT_MODEL", "claude-3-5-sonnet-20241022")
    monkeypatch.setenv("PROXY_TIMEOUT", "60")
    monkeypatch.setenv("PROXY_HOST", "0.0.0.0")
    monkeypatch.setenv("PROXY_PORT", "8080")

    config = ProxyConfig()

    assert config.default_model == "claude-3-5-sonnet-20241022"
    assert config.timeout == 60
    assert config.host == "0.0.0.0"
    assert config.port == 8080


def test_invalid_timeout_raises_error(monkeypatch):
    """Test that invalid timeout values raise error."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.test.com")
    monkeypatch.setenv("PROXY_API_KEY", "sk-ant-test123")
    monkeypatch.setenv("PROXY_TIMEOUT", "0")  # Below minimum

    with pytest.raises(ValidationError):
        ProxyConfig()


def test_invalid_port_raises_error(monkeypatch):
    """Test that invalid port values raise error."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.test.com")
    monkeypatch.setenv("PROXY_API_KEY", "sk-ant-test123")
    monkeypatch.setenv("PROXY_PORT", "99999")  # Above maximum

    with pytest.raises(ValidationError):
        ProxyConfig()
