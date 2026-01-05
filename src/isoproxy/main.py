"""Main FastAPI application for isoproxy."""

import logging
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from isoproxy.config import ProxyConfig
from isoproxy.errors import ProxyUpstreamError, proxy_upstream_error_handler
from isoproxy.models import MessagesRequest
from isoproxy.proxy import forward_to_upstream
from isoproxy.validation import prepare_request_payload

# Configure minimal logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("isoproxy")

# Load configuration at startup (fail fast on missing/invalid config)
try:
    config = ProxyConfig()
    logger.info(f"Proxy configuration loaded successfully")
    logger.info(f"Upstream: {config.upstream_base}")
    logger.info(f"Listening on: {config.host}:{config.port}")
    logger.info(f"Default model: {config.default_model or 'None (passthrough)'}")
    logger.info(f"Timeout: {config.timeout}s")
    logger.info(f"Passthrough mode: {'ENABLED' if config.passthrough else 'DISABLED'}")
except Exception as e:
    logger.error(f"Configuration error: {e}")
    raise

# Create FastAPI application
app = FastAPI(
    title="Isoproxy",
    description="Minimal Anthropic-compatible proxy for Claude Code",
    version="0.1.0",
    docs_url=None,  # Disable Swagger UI
    redoc_url=None,  # Disable ReDoc
)

# Register exception handlers
app.add_exception_handler(ProxyUpstreamError, proxy_upstream_error_handler)


@app.post("/v1/messages")
async def messages(request: Request) -> JSONResponse:
    """Handle POST /v1/messages - the only supported endpoint.

    This endpoint operates in two modes:
    - Normal mode: Validates request via Pydantic, applies model override
    - Passthrough mode: Bypasses all validation and forwards request directly

    Args:
        request: Raw FastAPI Request object

    Returns:
        JSONResponse with upstream status code and body

    Raises:
        HTTPException: On unexpected errors
        ProxyUpstreamError: On upstream failures (handled by exception handler)
    """
    try:
        if config.passthrough:
            # Passthrough mode: forward raw request body without validation
            raw_body = await request.body()
            try:
                payload = json.loads(raw_body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        else:
            # Normal mode: validate and process request
            raw_body = await request.body()
            try:
                request_data = json.loads(raw_body.decode('utf-8'))
                validated_request = MessagesRequest.model_validate(request_data)
                payload = prepare_request_payload(validated_request, config)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
            except Exception as e:
                raise HTTPException(status_code=422, detail=str(e))

        # Forward to upstream
        status_code, response_body = await forward_to_upstream(payload, config)

        # Return verbatim
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
async def catch_all(path: str, request: Request) -> JSONResponse:
    """Handle all other routes.

    In normal mode: Reject with 404 to maintain minimal attack surface
    In passthrough mode: Forward to upstream (for maximum compatibility)

    Args:
        path: The requested path
        request: Raw FastAPI Request object

    Returns:
        404 error response (normal mode) or upstream response (passthrough mode)
    """
    if config.passthrough:
        # Passthrough mode: forward any request to upstream
        try:
            import httpx
            raw_body = await request.body()
            
            # Construct upstream URL
            upstream_url = f"{config.upstream_base}/{path.lstrip('/')}"
            
            # Forward the request
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": request.headers.get("content-type", "application/json"),
            }
            
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                response = await client.request(
                    method=request.method,
                    url=upstream_url,
                    headers=headers,
                    content=raw_body,
                )
                
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            )
            
        except Exception as e:
            logger.error(f"Error in passthrough catch-all: {e}")
            raise HTTPException(status_code=502, detail="Bad gateway")
    else:
        # Normal mode: reject with 404
        raise HTTPException(status_code=404, detail="Not found")
