"""Configuration management for isoproxy."""

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProxyConfig(BaseSettings):
    """Configuration for the proxy server loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="PROXY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required configuration
    upstream_base: str = Field(
        ...,
        description="Base URL of the upstream Anthropic-compatible API",
    )
    api_key: str = Field(
        ...,
        description="API key for upstream authentication",
        min_length=1,
    )

    # Optional configuration
    default_model: str | None = Field(
        default=None,
        description="Default model to use if not specified in request",
    )
    timeout: int = Field(
        default=30,
        description="Timeout for upstream requests in seconds",
        ge=1,
        le=300,
    )
    host: str = Field(
        default="127.0.0.1",
        description="Host to bind the proxy server to",
    )
    port: int = Field(
        default=9000,
        description="Port to bind the proxy server to",
        ge=1,
        le=65535,
    )
    passthrough: bool = Field(
        default=False,
        description="Enable passthrough mode (bypasses all validation and filtering)",
    )

    @field_validator("upstream_base")
    @classmethod
    def validate_upstream_base(cls, v: str) -> str:
        """Validate that upstream_base is a valid HTTP/HTTPS URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("upstream_base must start with http:// or https://")
        # Remove trailing slash for consistency
        return v.rstrip("/")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that api_key is not a placeholder."""
        if v.lower() in ("dummy", "placeholder", "changeme", ""):
            raise ValueError("api_key must be a valid API key, not a placeholder")
        return v

    @property
    def upstream_url(self) -> str:
        """Construct the full upstream URL for the messages endpoint."""
        return f"{self.upstream_base}/v1/messages"
