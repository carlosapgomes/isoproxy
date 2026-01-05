"""Safe pass-through HTTP forwarding logic.

This module implements transparent forwarding with strict boundaries:
- No semantic inspection or modification of requests/responses
- Strict endpoint allowlisting
- Resource limits enforced
- Protocol fidelity preserved
"""

import logging
import json
from typing import Any, Dict, Tuple

import httpx

from isoproxy.config import ProxyConfig
from isoproxy.errors import ProxyUpstreamError

logger = logging.getLogger("isoproxy")


async def safe_forward_request(
    request_data: Dict[str, Any], 
    config: ProxyConfig
) -> Tuple[int, Dict[str, Any]]:
    """Safely forward request to upstream provider with strict boundaries.

    This function implements safe pass-through by:
    1. Enforcing endpoint allowlisting (no arbitrary URLs)
    2. Injecting credentials securely (agent never sees them)
    3. Preserving protocol fidelity (forward unknown fields)
    4. Enforcing resource limits (size, timeout)
    5. Returning responses verbatim (no semantic modification)

    Args:
        request_data: Raw request data as dictionary
        config: Proxy configuration with provider settings

    Returns:
        Tuple of (status_code, response_body) from upstream

    Raises:
        ProxyUpstreamError: On any failure (enforces fail-closed)
    """
    try:
        # Get provider configuration (enforced allowlist)
        upstream_url = config.get_upstream_endpoint()
        api_key = config.get_api_key()
        
        # Construct headers with credential injection
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        # Add Anthropic-specific headers if needed
        provider_config = config.get_active_provider_config()
        if "anthropic" in config.provider.lower():
            headers["anthropic-version"] = "2023-06-01"
        
        # Log metadata only (never request/response content)
        if config.logging_mode in ["metadata", "debug"]:
            logger.info(f"Forwarding to: {config.provider} endpoint")
            if config.logging_mode == "debug":
                logger.debug(f"Headers: {list(headers.keys())}")

        # Forward request with resource limits enforced
        async with httpx.AsyncClient(
            timeout=config.timeout_seconds,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            )
        ) as client:
            response = await client.post(
                upstream_url,
                json=request_data,  # Pass through verbatim
                headers=headers,
            )

            # Check response size limit
            response_size = len(response.content)
            if response_size > config.max_response_bytes:
                raise ProxyUpstreamError(
                    f"Response too large: {response_size} bytes (limit: {config.max_response_bytes})"
                )

            # Log response metadata
            if config.logging_mode in ["metadata", "debug"]:
                logger.info(f"Response: {response.status_code}, size: {response_size} bytes")

            # Return response verbatim - no error normalization in safe pass-through
            # The upstream provider's error format should be preserved for compatibility
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                # If not JSON, return as text in error format
                response_data = {"error": {"type": "proxy_error", "message": "Non-JSON response from provider"}}
                
            return response.status_code, response_data

    except httpx.TimeoutException as e:
        logger.error(f"Request timeout after {config.timeout_seconds}s")
        raise ProxyUpstreamError(f"Request timed out after {config.timeout_seconds}s")

    except httpx.RequestError as e:
        logger.error(f"Network error: {type(e).__name__}")
        raise ProxyUpstreamError(f"Network error: {type(e).__name__}")

    except Exception as e:
        logger.error(f"Unexpected error during request: {type(e).__name__}: {e}")
        raise ProxyUpstreamError(f"Unexpected error: {type(e).__name__}")


def validate_request_size(request_body: bytes, config: ProxyConfig) -> None:
    """Validate request size against configured limits.
    
    Args:
        request_body: Raw request body bytes
        config: Proxy configuration
        
    Raises:
        ProxyUpstreamError: If request exceeds size limits
    """
    if len(request_body) > config.max_request_bytes:
        raise ProxyUpstreamError(
            f"Request too large: {len(request_body)} bytes (limit: {config.max_request_bytes})"
        )


def parse_request_safely(request_body: bytes) -> Dict[str, Any]:
    """Parse request JSON with safe error handling.
    
    Args:
        request_body: Raw request body bytes
        
    Returns:
        Parsed JSON data
        
    Raises:
        ProxyUpstreamError: On JSON parsing errors
    """
    try:
        return json.loads(request_body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ProxyUpstreamError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ProxyUpstreamError(f"Request parsing error: {e}")