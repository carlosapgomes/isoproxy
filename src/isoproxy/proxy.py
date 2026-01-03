"""Upstream HTTP forwarding logic for isoproxy."""

import logging
from typing import Any

import httpx

from isoproxy.config import ProxyConfig
from isoproxy.errors import ProxyUpstreamError

logger = logging.getLogger("isoproxy")


async def forward_to_upstream(payload: dict, config: ProxyConfig) -> tuple[int, dict[str, Any]]:
    """Forward request to upstream Anthropic-compatible API.

    This function:
    1. Creates an async HTTP client with configured timeout
    2. Sends POST request to upstream with proper headers
    3. Returns upstream response verbatim on success
    4. Raises ProxyUpstreamError on any failure (timeout, network, etc.)

    Note: Request and response bodies are never logged per security requirements.

    Args:
        payload: Request payload as dictionary (ready for JSON serialization)
        config: Proxy configuration containing upstream URL and API key

    Returns:
        Tuple of (status_code, response_body) from upstream

    Raises:
        ProxyUpstreamError: On any timeout, network error, or HTTP error
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}",
        "anthropic-version": "2023-06-01",  # Required by Anthropic API
    }

    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.post(
                config.upstream_url,
                json=payload,
                headers=headers,
            )

            # Return response verbatim (don't validate or modify)
            # The upstream might return 4xx/5xx which we pass through
            return response.status_code, response.json()

    except httpx.TimeoutException as e:
        logger.error(f"Upstream timeout after {config.timeout}s: {type(e).__name__}")
        raise ProxyUpstreamError(f"Upstream request timed out after {config.timeout}s")

    except httpx.RequestError as e:
        logger.error(f"Upstream network error: {type(e).__name__}")
        raise ProxyUpstreamError(f"Upstream network error: {type(e).__name__}")

    except Exception as e:
        # Catch any other unexpected errors (JSON decode, etc.)
        logger.error(f"Unexpected error during upstream request: {type(e).__name__}")
        raise ProxyUpstreamError(f"Unexpected upstream error: {type(e).__name__}")
