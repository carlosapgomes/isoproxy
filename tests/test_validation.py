"""Tests for request validation and processing."""

import pytest
from pydantic import ValidationError

from isoproxy.models import Message, MessagesRequest
from isoproxy.validation import apply_model_override, prepare_request_payload


def test_valid_request_passes_validation():
    """Test that a valid request passes Pydantic validation."""
    request = MessagesRequest(
        model="claude-3-5-sonnet-20241022",
        messages=[Message(role="user", content="Hello")],
        max_tokens=1024,
    )

    assert request.model == "claude-3-5-sonnet-20241022"
    assert len(request.messages) == 1
    assert request.stream is False


def test_missing_messages_raises_error():
    """Test that missing messages field raises validation error."""
    with pytest.raises(ValidationError):
        MessagesRequest(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
        )


def test_empty_messages_raises_error():
    """Test that empty messages array raises validation error."""
    with pytest.raises(ValidationError):
        MessagesRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[],
            max_tokens=1024,
        )


def test_stream_true_raises_error():
    """Test that stream=true raises validation error."""
    with pytest.raises(ValidationError, match="Streaming is not supported"):
        MessagesRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="Hello")],
            max_tokens=1024,
            stream=True,
        )


def test_model_override_applied_when_configured(mock_config_with_default_model):
    """Test that model override is applied when PROXY_DEFAULT_MODEL is set."""
    # Create a request with a different model
    request = MessagesRequest(
        model="claude-3-opus-20240229",  # Different from default
        messages=[Message(role="user", content="Hello")],
        max_tokens=1024,
    )
    original_model = request.model
    result = apply_model_override(request, mock_config_with_default_model)

    assert result.model == "claude-3-5-sonnet-20241022"
    assert result.model != original_model


def test_model_override_not_applied_when_not_configured(mock_config, valid_request):
    """Test that model override is not applied when PROXY_DEFAULT_MODEL is unset."""
    original_model = valid_request.model
    result = apply_model_override(valid_request, mock_config)

    assert result.model == original_model


def test_prepare_request_payload_returns_dict(mock_config, valid_request):
    """Test that prepare_request_payload returns a dictionary."""
    payload = prepare_request_payload(valid_request, mock_config)

    assert isinstance(payload, dict)
    assert "model" in payload
    assert "messages" in payload
    assert "max_tokens" in payload


def test_prepare_request_payload_excludes_none_values(mock_config):
    """Test that None values are excluded from the payload."""
    request = MessagesRequest(
        model="claude-3-5-sonnet-20241022",
        messages=[Message(role="user", content="Hello")],
        max_tokens=1024,
        temperature=None,  # Should be excluded
    )

    payload = prepare_request_payload(request, mock_config)

    assert "temperature" not in payload


def test_prepare_request_payload_includes_optional_values(mock_config):
    """Test that non-None optional values are included in the payload."""
    request = MessagesRequest(
        model="claude-3-5-sonnet-20241022",
        messages=[Message(role="user", content="Hello")],
        max_tokens=1024,
        temperature=0.7,
        top_p=0.9,
    )

    payload = prepare_request_payload(request, mock_config)

    assert payload["temperature"] == 0.7
    assert payload["top_p"] == 0.9


def test_prepare_request_payload_applies_model_override(
    mock_config_with_default_model, valid_request
):
    """Test that prepare_request_payload applies model override."""
    payload = prepare_request_payload(valid_request, mock_config_with_default_model)

    assert payload["model"] == "claude-3-5-sonnet-20241022"
