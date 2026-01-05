"""Minimal models for safe pass-through proxy.

This module defines only the absolute minimum models needed for
proxy operation. No semantic validation or content filtering.
"""

from typing import Any, Literal, Dict
from pydantic import BaseModel


class ProxyRequest(BaseModel):
    """Minimal wrapper for any JSON request.
    
    Used only for size validation - content is passed through unchanged.
    """
    
    # Accept any fields - we don't validate content
    model_config = {"extra": "allow"}
    
    def __init__(self, **data):
        """Initialize with any data - no validation."""
        super().__init__(**data)


class ErrorDetail(BaseModel):
    """Error detail in error responses."""

    type: str
    message: str


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    type: Literal["error"] = "error"
    error: ErrorDetail
