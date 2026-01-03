"""Error handling and custom exceptions for isoproxy."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("isoproxy")


class ProxyUpstreamError(Exception):
    """Raised when upstream request fails (timeout, network error, etc.)."""

    pass


# Error mapping: upstream status code -> (error_type, message)
# This prevents leaking upstream provider details to the sandbox
UPSTREAM_ERROR_MAP = {
    400: ("invalid_request", "The request was malformed or missing required parameters"),
    401: ("authentication_error", "Authentication failed"),
    403: ("permission_denied", "Access to the requested resource is forbidden"),
    404: ("not_found", "The requested resource was not found"),
    429: ("rate_limited", "Rate limit exceeded"),
    500: ("upstream_error", "The provider encountered an internal error"),
    502: ("upstream_error", "The provider is temporarily unavailable"),
    503: ("upstream_error", "The provider is temporarily unavailable"),
    529: ("upstream_error", "The provider is temporarily overloaded"),
}


def create_error_response(error_type: str, message: str) -> dict:
    """Create a standardized error response.

    Args:
        error_type: Type of error (e.g., "proxy_error")
        message: Human-readable error message

    Returns:
        Dictionary matching ErrorResponse schema
    """
    return {"type": "error", "error": {"type": error_type, "message": message}}


def normalize_upstream_error(status_code: int) -> tuple[int, dict]:
    """Normalize upstream error responses to prevent information leakage.

    Maps upstream status codes to standardized error responses that preserve
    semantic signal (auth vs rate limit vs server error) while hiding
    provider-specific details like error taxonomy, rate limit numbers, etc.

    Args:
        status_code: HTTP status code from upstream

    Returns:
        Tuple of (status_code, standardized_error_body)
    """
    # Map known error codes to standardized responses
    if status_code in UPSTREAM_ERROR_MAP:
        error_type, message = UPSTREAM_ERROR_MAP[status_code]
        return status_code, create_error_response(error_type, message)

    # For unknown 4xx errors, return generic client error
    if 400 <= status_code < 500:
        return status_code, create_error_response(
            "client_error", "The request could not be processed"
        )

    # For unknown 5xx errors, return generic server error
    if status_code >= 500:
        return status_code, create_error_response(
            "upstream_error", "The provider encountered an error"
        )

    # Should never reach here for error codes, but handle defensively
    logger.warning(f"Unexpected status code in error normalization: {status_code}")
    return 502, create_error_response("upstream_error", "Unexpected provider response")


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
