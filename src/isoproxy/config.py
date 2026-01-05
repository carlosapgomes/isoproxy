"""Configuration management for isoproxy safe pass-through proxy."""

import os
from typing import Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProxyConfig(BaseSettings):
    """Configuration for the safe pass-through proxy server.
    
    This configuration enforces strict boundaries while allowing transparent
    protocol forwarding to Anthropic-compatible providers.
    """

    model_config = SettingsConfigDict(
        env_prefix="PROXY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provider Configuration
    providers: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "anthropic": {
                "endpoint": "https://api.anthropic.com",
                "api_key_env": "ANTHROPIC_API_KEY"
            }
        },
        description="Provider configurations with endpoints and credentials"
    )
    
    # Active provider (must be in allowlist)
    provider: str = Field(
        default="anthropic",
        description="Active provider name (must exist in providers config)"
    )

    # Resource Limits (MUST enforce)
    max_request_bytes: int = Field(
        default=5 * 1024 * 1024,  # 5MB
        description="Maximum request body size in bytes",
        ge=1024,  # Minimum 1KB
    )
    max_response_bytes: int = Field(
        default=20 * 1024 * 1024,  # 20MB
        description="Maximum response body size in bytes", 
        ge=1024,
    )
    timeout_seconds: int = Field(
        default=120,
        description="Timeout for upstream requests in seconds",
        ge=1,
        le=600,  # Max 10 minutes
    )

    # Server Configuration
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


    # Logging Configuration
    logging_mode: str = Field(
        default="metadata",
        description="Logging mode: off, metadata, or debug"
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str, info) -> str:
        """Validate that provider exists in allowlist."""
        providers = info.data.get("providers", {})
        if v not in providers:
            raise ValueError(f"Provider '{v}' not in allowlist: {list(providers.keys())}")
        return v

    @field_validator("logging_mode")
    @classmethod
    def validate_logging_mode(cls, v: str) -> str:
        """Validate logging mode is one of the allowed values."""
        allowed = {"off", "metadata", "debug"}
        if v not in allowed:
            raise ValueError(f"logging_mode must be one of: {allowed}")
        return v

    def get_active_provider_config(self) -> Dict[str, Any]:
        """Get configuration for the active provider."""
        return self.providers[self.provider]
    
    def get_upstream_endpoint(self) -> str:
        """Get the upstream endpoint URL for the active provider."""
        provider_config = self.get_active_provider_config()
        endpoint = provider_config["endpoint"].rstrip("/")
        return f"{endpoint}/v1/messages"
    
    def get_api_key(self) -> str:
        """Get API key for the active provider from environment."""
        provider_config = self.get_active_provider_config()
        env_var = provider_config["api_key_env"]
        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(f"API key not found in environment variable: {env_var}")
        return api_key
