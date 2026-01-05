"""Error handling for safe pass-through proxy.

This module provides minimal error handling that preserves upstream
error responses for protocol fidelity while preventing sensitive
information leakage.
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("isoproxy")


class ProxyUpstreamError(Exception):
    """Raised when upstream request fails (timeout, network error, etc.)."""

    pass


def create_error_response(error_type: str, message: str) -> dict:
    """Create a standardized error response for proxy-level errors.

    Only used for proxy-specific errors, not upstream provider errors.
    Upstream errors are passed through unchanged for protocol fidelity.

    Args:
        error_type: Type of error (e.g., "proxy_error")
        message: Human-readable error message

    Returns:
        Dictionary matching ErrorResponse schema
    """
    return {"type": "error", "error": {"type": error_type, "message": message}}


async def proxy_upstream_error_handler(
    request: Request, exc: ProxyUpstreamError
) -> JSONResponse:
    """Handle proxy-level upstream failures.

    This handler only deals with proxy-level errors like network failures,
    timeouts, or connection issues. It does NOT normalize upstream provider
    error responses, which are passed through unchanged.

    Args:
        request: The FastAPI request object
        exc: The ProxyUpstreamError exception

    Returns:
        JSONResponse with 502 status and proxy error
    """
    # Log the error without sensitive details
    logger.error(f"Proxy upstream error: {exc}")

    # Return proxy-level 502 error
    return JSONResponse(
        status_code=502,
        content=create_error_response("proxy_error", str(exc)),
    )
