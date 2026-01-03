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
async def test_upstream_4xx_error_returned_verbatim(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that upstream 4xx errors are returned verbatim."""
    error_response = {
        "type": "error",
        "error": {"type": "invalid_request_error", "message": "Invalid model"},
    }

    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json=error_response,
        status_code=400,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    assert status_code == 400
    assert response_body == error_response


@pytest.mark.asyncio
async def test_upstream_5xx_error_returned_verbatim(
    mock_config, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that upstream 5xx errors are returned verbatim."""
    error_response = {
        "type": "error",
        "error": {"type": "api_error", "message": "Internal server error"},
    }

    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json=error_response,
        status_code=500,
    )

    status_code, response_body = await forward_to_upstream(valid_request_dict, mock_config)

    assert status_code == 500
    assert response_body == error_response


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
