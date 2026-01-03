"""Request validation and processing logic for isoproxy."""

from isoproxy.config import ProxyConfig
from isoproxy.models import MessagesRequest


def apply_model_override(request: MessagesRequest, config: ProxyConfig) -> MessagesRequest:
    """Apply model override if PROXY_DEFAULT_MODEL is configured.

    Args:
        request: The incoming messages request
        config: Proxy configuration

    Returns:
        Request with potentially overridden model field
    """
    if config.default_model:
        request.model = config.default_model
    return request


def prepare_request_payload(request: MessagesRequest, config: ProxyConfig) -> dict:
    """Prepare the final request payload for upstream forwarding.

    This function:
    1. Applies model override if configured
    2. Converts the Pydantic model to a dictionary
    3. Excludes None values for cleaner JSON

    Args:
        request: The incoming messages request
        config: Proxy configuration

    Returns:
        Dictionary ready for JSON serialization and upstream forwarding
    """
    # Apply model override
    request = apply_model_override(request, config)

    # Convert to dict, excluding None values
    return request.model_dump(exclude_none=True)
