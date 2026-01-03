"""Pytest fixtures for isoproxy tests."""

import pytest
from isoproxy.config import ProxyConfig
from isoproxy.models import Message, MessagesRequest


@pytest.fixture
def mock_config(monkeypatch):
    """Provide test configuration via environment variables."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.test.com")
    monkeypatch.setenv("PROXY_API_KEY", "test-key-123")
    monkeypatch.setenv("PROXY_TIMEOUT", "10")
    return ProxyConfig()


@pytest.fixture
def mock_config_with_default_model(monkeypatch):
    """Provide test configuration with default model override."""
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.test.com")
    monkeypatch.setenv("PROXY_API_KEY", "test-key-123")
    monkeypatch.setenv("PROXY_DEFAULT_MODEL", "claude-3-5-sonnet-20241022")
    return ProxyConfig()


@pytest.fixture
def valid_request():
    """Provide a valid MessagesRequest."""
    return MessagesRequest(
        model="claude-3-5-sonnet-20241022",
        messages=[Message(role="user", content="Hello")],
        max_tokens=1024,
    )


@pytest.fixture
def valid_request_dict():
    """Provide a valid request as a dictionary."""
    return {
        "model": "claude-3-5-sonnet-20241022",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 1024,
    }


@pytest.fixture
def mock_upstream_success_response():
    """Provide a mock successful upstream response."""
    return {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Hello! How can I help you?"}],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }
