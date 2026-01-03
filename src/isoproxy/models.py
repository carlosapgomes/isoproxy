"""Pydantic models for Anthropic Messages API request/response schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Message(BaseModel):
    """A single message in the conversation."""

    role: Literal["user", "assistant"]
    content: str | list[dict[str, Any]]


class MessagesRequest(BaseModel):
    """Request schema for the Anthropic Messages API."""

    model: str = Field(..., description="Model identifier")
    messages: list[Message] = Field(..., min_length=1, description="Conversation messages")
    max_tokens: int = Field(..., ge=1, description="Maximum tokens to generate")

    # Optional parameters
    metadata: dict[str, Any] | None = None
    stop_sequences: list[str] | None = None
    stream: bool = False
    system: str | list[dict[str, Any]] | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_no_streaming(self) -> "MessagesRequest":
        """Reject streaming requests as per spec."""
        if self.stream:
            raise ValueError("Streaming is not supported by this proxy")
        return self


class ErrorDetail(BaseModel):
    """Error detail in error responses."""

    type: str
    message: str


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    type: Literal["error"] = "error"
    error: ErrorDetail
