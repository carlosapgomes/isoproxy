"""Tests for upstream proxy forwarding."""

import pytest
from pytest_httpx import HTTPXMock

from isoproxy.errors import ProxyUpstreamError
from isoproxy.proxy import forward_to_upstream


@pytest.mark.asyncio
async def test_successful_upstream_request_returns_verbatim(
    mock_config, valid_request_dict, mock_upstream_success_response, httpx_mock: HTTPXMock
):
    """Test that successful upstream requests return verbatim response."""
    # Mock the upstream API response
    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json=mock_upstream_success_response,
        status_code=200,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    assert status_code == 200
    assert response_body == mock_upstream_success_response


@pytest.mark.asyncio
async def test_upstream_400_error_normalized(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that upstream 400 errors are normalized to prevent info leakage."""
    # Upstream returns provider-specific error
    upstream_error = {
        "type": "error",
        "error": {
            "type": "invalid_request_error",
            "message": "Anthropic-specific error details",
        },
    }

    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json=upstream_error,
        status_code=400,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    # Status code preserved, but error details are normalized
    assert status_code == 400
    assert response_body == {
        "type": "error",
        "error": {
            "type": "invalid_request",
            "message": "The request was malformed or missing required parameters",
        },
    }


@pytest.mark.asyncio
async def test_upstream_401_error_normalized(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that upstream 401 errors are normalized."""
    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json={"error": "Invalid API key"},
        status_code=401,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    assert status_code == 401
    assert response_body == {
        "type": "error",
        "error": {"type": "authentication_error", "message": "Authentication failed"},
    }


@pytest.mark.asyncio
async def test_upstream_429_error_normalized(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that upstream 429 errors are normalized to hide rate limit details."""
    # Upstream might return detailed rate limit info
    upstream_error = {
        "error": {
            "type": "rate_limit_error",
            "message": "Rate limit: 50 requests per minute, retry after 30s",
        }
    }

    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json=upstream_error,
        status_code=429,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    assert status_code == 429
    assert response_body == {
        "type": "error",
        "error": {"type": "rate_limited", "message": "Rate limit exceeded"},
    }


@pytest.mark.asyncio
async def test_upstream_500_error_normalized(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that upstream 500 errors are normalized."""
    upstream_error = {
        "type": "error",
        "error": {"type": "api_error", "message": "Internal server error details"},
    }

    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json=upstream_error,
        status_code=500,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    assert status_code == 500
    assert response_body == {
        "type": "error",
        "error": {
            "type": "upstream_error",
            "message": "The provider encountered an internal error",
        },
    }


@pytest.mark.asyncio
async def test_upstream_timeout_raises_proxy_error(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that upstream timeout raises ProxyUpstreamError."""
    import httpx

    # Simulate timeout by raising TimeoutException
    def timeout_callback(request):
        raise httpx.TimeoutException("Request timed out", request=request)

    httpx_mock.add_callback(timeout_callback)

    with pytest.raises(ProxyUpstreamError, match="timed out"):
        await forward_to_upstream(valid_request_dict, mock_config)


@pytest.mark.asyncio
async def test_network_error_raises_proxy_error(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that network errors raise ProxyUpstreamError."""
    import httpx

    # Simulate network error
    def network_error_callback(request):
        raise httpx.ConnectError("Connection failed", request=request)

    httpx_mock.add_callback(network_error_callback)

    with pytest.raises(ProxyUpstreamError, match="network error"):
        await forward_to_upstream(valid_request_dict, mock_config)


@pytest.mark.asyncio
async def test_correct_headers_sent_to_upstream(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that correct headers are sent to upstream."""
    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json={"id": "msg_123"},
        status_code=200,
    )

    await forward_to_upstream(valid_request_dict, mock_config)

    # Verify the request was made with correct headers
    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer test-key-123"
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["anthropic-version"] == "2023-06-01"


@pytest.mark.asyncio
async def test_correct_url_called(mock_config, valid_request_dict, httpx_mock: HTTPXMock):
    """Test that the correct upstream URL is called."""
    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json={"id": "msg_123"},
        status_code=200,
    )

    await forward_to_upstream(valid_request_dict, mock_config)

    request = httpx_mock.get_request()
    assert str(request.url) == "https://api.test.com/v1/messages"


@pytest.mark.asyncio
async def test_unknown_4xx_error_normalized(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that unknown 4xx errors get generic client error message."""
    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json={"error": "Some provider-specific 418 error"},
        status_code=418,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    # Status code preserved, but message is generic
    assert status_code == 418
    assert response_body == {
        "type": "error",
        "error": {"type": "client_error", "message": "The request could not be processed"},
    }


@pytest.mark.asyncio
async def test_unknown_5xx_error_normalized(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that unknown 5xx errors get generic upstream error message."""
    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json={"error": "Some provider-specific 599 error"},
        status_code=599,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    # Status code preserved, but message is generic
    assert status_code == 599
    assert response_body == {
        "type": "error",
        "error": {"type": "upstream_error", "message": "The provider encountered an error"},
    }


@pytest.mark.asyncio
async def test_multiple_mapped_errors(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that all mapped error codes return correct normalized responses."""
    test_cases = [
        (403, "permission_denied", "Access to the requested resource is forbidden"),
        (404, "not_found", "The requested resource was not found"),
        (502, "upstream_error", "The provider is temporarily unavailable"),
        (503, "upstream_error", "The provider is temporarily unavailable"),
        (529, "upstream_error", "The provider is temporarily overloaded"),
    ]

    for status, error_type, message in test_cases:
        httpx_mock.add_response(
            url="https://api.test.com/v1/messages",
            method="POST",
            json={"original": "error"},
            status_code=status,
        )

        result_status, result_body = await forward_to_upstream(
            valid_request_dict, mock_config
        )

        assert result_status == status
        assert result_body == {
            "type": "error",
            "error": {"type": error_type, "message": message},
        }
