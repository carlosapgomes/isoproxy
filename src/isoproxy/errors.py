"""Error handling and custom exceptions for isoproxy."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("isoproxy")


class ProxyUpstreamError(Exception):
    """Raised when upstream request fails (timeout, network error, etc.)."""

    pass


def create_error_response(error_type: str, message: str) -> dict:
    """Create a standardized error response.

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
    """Handle upstream failures by returning 502 with standardized error.

    This handler is registered with FastAPI and catches ProxyUpstreamError
    exceptions. It logs the error (without request/response bodies) and
    returns a generic 502 error to avoid leaking upstream provider details.

    Args:
        request: The FastAPI request object
        exc: The ProxyUpstreamError exception

    Returns:
        JSONResponse with 502 status and standardized error body
    """
    # Log the error without sensitive details
    logger.error(f"Upstream request failed: {exc}")

    # Return standardized 502 error
    return JSONResponse(
        status_code=502,
        content=create_error_response("proxy_error", "Upstream request failed"),
    )
