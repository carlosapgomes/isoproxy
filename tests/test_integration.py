"""Integration tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock


@pytest.fixture
def client(monkeypatch):
    """Create a test client for the FastAPI app."""
    # Set required environment variables before importing the app
    monkeypatch.setenv("PROXY_UPSTREAM_BASE", "https://api.test.com")
    monkeypatch.setenv("PROXY_API_KEY", "test-key-123")

    # Import after setting env vars to ensure config loads correctly
    from isoproxy.main import app

    return TestClient(app)


def test_post_v1_messages_returns_200_on_success(
    client, valid_request_dict, mock_upstream_success_response, httpx_mock: HTTPXMock
):
    """Test that POST /v1/messages returns 200 on success."""
    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json=mock_upstream_success_response,
        status_code=200,
    )

    response = client.post("/v1/messages", json=valid_request_dict)

    assert response.status_code == 200
    assert response.json() == mock_upstream_success_response


def test_post_v1_messages_returns_502_on_upstream_failure(
    client, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that POST /v1/messages returns 502 on upstream failure."""
    import httpx

    # Simulate network error
    def network_error_callback(request, ext):
        raise httpx.ConnectError("Connection failed", request=request)

    httpx_mock.add_callback(network_error_callback)

    response = client.post("/v1/messages", json=valid_request_dict)

    assert response.status_code == 502
    body = response.json()
    assert body["type"] == "error"
    assert body["error"]["type"] == "proxy_error"
    assert body["error"]["message"] == "Upstream request failed"


def test_post_v1_messages_returns_422_on_validation_error(client):
    """Test that POST /v1/messages returns 422 on validation error."""
    invalid_request = {
        "model": "claude-3-5-sonnet-20241022",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 1024,
        "stream": True,  # Not allowed
    }

    response = client.post("/v1/messages", json=invalid_request)

    assert response.status_code == 422


def test_get_v1_messages_returns_405(client):
    """Test that GET /v1/messages returns 405 method not allowed."""
    response = client.get("/v1/messages")

    assert response.status_code == 405


def test_post_other_path_returns_404(client):
    """Test that POST to other paths returns 404."""
    response = client.post("/v1/completions", json={})

    assert response.status_code == 404


def test_get_root_returns_404(client):
    """Test that GET / returns 404."""
    response = client.get("/")

    assert response.status_code == 404


def test_response_matches_upstream_verbatim(
    client, valid_request_dict, httpx_mock: HTTPXMock
):
    """Test that error responses are normalized to prevent info leakage."""
    # Upstream returns provider-specific error details
    upstream_error = {
        "type": "error",
        "error": {
            "type": "rate_limit_error",
            "message": "Rate limit: 50 requests per minute, retry after 30s",
        },
    }

    httpx_mock.add_response(
        url="https://api.test.com/v1/messages",
        method="POST",
        json=upstream_error,
        status_code=429,
    )

    response = client.post("/v1/messages", json=valid_request_dict)

    # Status code preserved, but error details are normalized
    assert response.status_code == 429
    assert response.json() == {
        "type": "error",
        "error": {"type": "rate_limited", "message": "Rate limit exceeded"},
    }


def test_missing_messages_field_returns_422(client):
    """Test that missing messages field returns 422."""
    invalid_request = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
    }

    response = client.post("/v1/messages", json=invalid_request)

    assert response.status_code == 422


def test_invalid_json_returns_422(client):
    """Test that invalid JSON returns 422."""
    response = client.post(
        "/v1/messages",
        data="not json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
