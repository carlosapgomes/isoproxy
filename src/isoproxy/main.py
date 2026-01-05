"""Safe pass-through proxy main application.

This module implements a safe pass-through proxy following these principles:
- Strict endpoint allowlisting (no arbitrary URL forwarding)
- Protocol preservation (forward unknown fields unchanged)
- Resource boundaries (size/timeout limits enforced)
- Credential isolation (agent never sees API keys)
- Transparent operation (minimal semantic interpretation)
"""

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from isoproxy.config import ProxyConfig
from isoproxy.errors import ProxyUpstreamError, proxy_upstream_error_handler
from isoproxy.proxy import safe_forward_request, validate_request_size, parse_request_safely

# Configure logging based on config (will be updated after config load)
logger = logging.getLogger("isoproxy")

# Load configuration at startup (fail fast on missing/invalid config)
try:
    config = ProxyConfig()
    
    # Configure logging level based on config
    if config.logging_mode == "off":
        logging.getLogger("isoproxy").setLevel(logging.CRITICAL)
    elif config.logging_mode == "debug":
        logging.getLogger("isoproxy").setLevel(logging.DEBUG)
    else:  # metadata
        logging.getLogger("isoproxy").setLevel(logging.INFO)
    
    # Set up logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True
    )
    
    # Log startup info (metadata only)
    logger.info("Safe pass-through proxy starting")
    logger.info(f"Active provider: {config.provider}")
    logger.info(f"Listening on: {config.host}:{config.port}")
    logger.info(f"Request limit: {config.max_request_bytes} bytes")
    logger.info(f"Response limit: {config.max_response_bytes} bytes")
    logger.info(f"Timeout: {config.timeout_seconds}s")
    logger.info(f"Logging mode: {config.logging_mode}")
    
except Exception as e:
    logger.error(f"Configuration error: {e}")
    raise

# Create FastAPI application
app = FastAPI(
    title="Isoproxy Safe Pass-Through",
    description="Safe pass-through proxy for Anthropic-compatible APIs",
    version="2.0.0",
    docs_url=None,  # Disable Swagger UI (reduce attack surface)
    redoc_url=None,  # Disable ReDoc
)

# Register exception handlers
app.add_exception_handler(ProxyUpstreamError, proxy_upstream_error_handler)


@app.post("/v1/messages")
async def messages_endpoint(request: Request) -> JSONResponse:
    """Handle POST /v1/messages - safe pass-through to upstream provider.

    This endpoint implements safe pass-through by:
    1. Validating request size limits (no semantic validation)
    2. Forwarding request verbatim to allowlisted provider endpoint
    3. Returning upstream response unchanged (preserves protocol fidelity)
    4. Never exposing credentials to the agent

    Args:
        request: Raw FastAPI Request object

    Returns:
        JSONResponse with upstream status code and body (unchanged)

    Raises:
        HTTPException: On request size limits or parsing errors
        ProxyUpstreamError: On upstream failures (handled by exception handler)
    """
    try:
        # Get raw request body
        raw_body = await request.body()
        
        # Enforce request size limits (MUST enforce)
        validate_request_size(raw_body, config)
        
        # Parse JSON safely (no semantic validation)
        request_data = parse_request_safely(raw_body)
        
        # Log metadata only
        if config.logging_mode in ["metadata", "debug"]:
            logger.info(f"Request received, size: {len(raw_body)} bytes")
        
        # Forward to upstream with safe pass-through
        status_code, response_body = await safe_forward_request(request_data, config)

        # Return verbatim (preserve all provider-specific fields)
        return JSONResponse(
            status_code=status_code,
            content=response_body,
        )

    except ProxyUpstreamError:
        # Let the exception handler deal with it
        raise

    except Exception as e:
        # Catch any unexpected programming errors
        logger.error(f"Unexpected error in /v1/messages: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@app.api_route("/v1/messages", methods=["GET", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def messages_method_not_allowed() -> JSONResponse:
    """Reject non-POST requests to /v1/messages with 405."""
    raise HTTPException(status_code=405, detail="Method not allowed")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all_reject(path: str) -> JSONResponse:
    """Reject all other routes with 404.
    
    Safe pass-through mode only supports /v1/messages endpoint.
    All other paths are rejected to maintain minimal attack surface.
    
    This differs from the old "passthrough mode" which would forward
    arbitrary paths - that violated the safe pass-through design principle
    of strict endpoint allowlisting.
    
    Args:
        path: The requested path

    Returns:
        404 error response
    """
    logger.warning(f"Blocked request to disallowed path: /{path}")
    raise HTTPException(status_code=404, detail="Endpoint not allowed")


@app.get("/health")
async def health_check() -> JSONResponse:
    """Basic health check endpoint.
    
    Returns basic status without exposing sensitive configuration details.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "proxy": "safe-pass-through", 
            "provider": config.provider
        }
    )