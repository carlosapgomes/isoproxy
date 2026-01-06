# Isoproxy

**Safe Pass-Through Proxy for Sandboxed Environments**

Isoproxy is a safe pass-through proxy server designed specifically for [papercage](https://github.com/carlosapgomes/papercage) and other sandboxed environments. It enables secure API access from isolated agents through Unix domain sockets while maintaining strict security boundaries.

> **IMPORTANT**: This proxy does not attempt to make model output safe. Safety in this architecture comes from sandboxing (papercage), filesystem isolation, human review, and version control. The proxy's role is to be boring, predictable, and hard to misuse by accident.

## Primary Use Case: Papercage Integration

```
Agent (in papercage sandbox) <--UDS--> Isoproxy (outside) <--HTTPS--> Inference Provider
```

The proxy runs **outside** the sandbox environment and accepts connections from sandboxed agents via Unix domain sockets, providing the only controlled path for API access.

## Features

### Safe Pass-Through Design

- **Strict endpoint allowlisting**: Only connects to configured provider endpoints (no arbitrary URLs)
- **Protocol preservation**: Forwards unknown fields unchanged for maximum compatibility
- **Resource boundaries**: Enforces request/response size limits and timeouts
- **Credential isolation**: API keys never exposed to agents, injected securely by proxy
- **Transparent operation**: No semantic filtering, content rewriting, or "smart" behavior

### Security Boundaries

- **Minimal attack surface**: Only supports `POST /v1/messages` and `/health`
- **Fail-closed design**: Strict validation of configuration and resource limits
- **Metadata-only logging**: Request/response content never logged by default
- **No arbitrary forwarding**: Rejects all non-allowlisted endpoints

### Sandboxed Environment Integration

- **Unix domain socket binding**: Default server mode for sandboxed agents
- **Papercage optimized**: Designed specifically for papercage sandbox integration
- **Multi-provider support**: Anthropic and other Anthropic-compatible APIs
- **Protocol fidelity**: Preserves streaming, model negotiation, and provider extensions

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Quick Start

### 1. Installation

```bash
# Clone or download the repository
cd isoproxy

# Create virtual environment and install dependencies with uv
uv venv
uv pip install -e .

# Or with pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configuration

Copy the example configuration:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Provider selection (must be in allowlist)
PROXY_PROVIDER=anthropic

# Provider configurations
PROXY_PROVIDERS={
  "anthropic": {
    "endpoint": "https://api.anthropic.com",
    "api_key_env": "ANTHROPIC_API_KEY"
  }
}

# Resource limits (enforced strictly)
PROXY_MAX_REQUEST_BYTES=5242880    # 5MB
PROXY_MAX_RESPONSE_BYTES=20971520  # 20MB
PROXY_TIMEOUT_SECONDS=120          # 2 minutes

# Server configuration
PROXY_HOST=127.0.0.1
PROXY_PORT=9000

# Logging mode (off | metadata | debug)
PROXY_LOGGING_MODE=metadata
```

Set your API keys in separate environment variables:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-api-key-here
# export PROXY_TIMEOUT=60
```

Alternatively, copy `deployment/.env.example` to `.env` and fill in your values:

```bash
cp deployment/.env.example .env
# Edit .env with your favorite editor
```

### 3. Run the Proxy

**For papercage integration (recommended):**

```bash
# Production mode with Unix domain socket (default for sandboxes)
uvicorn isoproxy.main:app --uds /run/isoproxy/isoproxy.sock --workers 1
```

**For development/testing:**

```bash
# Development mode with HTTP (for testing outside sandbox)
uvicorn isoproxy.main:app --reload --host 127.0.0.1 --port 9000
```

### 4. Configure Sandboxed Agent

**For papercage (Unix domain socket):**
Configure the agent to connect via Unix socket at `/run/isoproxy/isoproxy.sock`

**For development/testing (HTTP):**

```bash
export ANTHROPIC_API_BASE=http://127.0.0.1:9000
export ANTHROPIC_API_KEY=dummy  # Ignored by proxy
```

The agent will now use the proxy to access the upstream API through the configured transport.

## Configuration Reference

| Environment Variable       | Required | Default                | Description                                                  |
| -------------------------- | -------- | ---------------------- | ------------------------------------------------------------ |
| `PROXY_PROVIDER`           | No       | `anthropic`            | Active provider name (must exist in `PROXY_PROVIDERS`)       |
| `PROXY_PROVIDERS`          | No       | `{"anthropic": {...}}` | JSON dict of provider configurations                         |
| `PROXY_MAX_REQUEST_BYTES`  | No       | `5242880`              | Maximum request size in bytes (5MB)                          |
| `PROXY_MAX_RESPONSE_BYTES` | No       | `20971520`             | Maximum response size in bytes (20MB)                        |
| `PROXY_TIMEOUT_SECONDS`    | No       | `120`                  | Timeout for upstream requests (1-600 seconds)                |
| `PROXY_HOST`               | No       | `127.0.0.1`            | Host to bind proxy server to                                 |
| `PROXY_PORT`               | No       | `9000`                 | Port to bind proxy server to                                 |
| `PROXY_LOGGING_MODE`       | No       | `metadata`             | Logging mode: `off`, `metadata`, or `debug`                  |
| `ANTHROPIC_API_KEY`        | Yes\*    | -                      | API key for Anthropic (required if using anthropic provider) |

\*Required depending on which provider is configured.

## Provider Compatibility

**IMPORTANT**: Isoproxy is designed specifically for **Claude Code**, which is the only LLM coding assistant that uses Anthropic's API protocol. On the server side, isoproxy works with **Anthropic-compatible** API endpoints that use the Anthropic protocol format. This includes:

✅ **Compatible providers:**

- Anthropic (api.anthropic.com) - native support
- Z.ai GLM-4.7 - offers Anthropic-compatible endpoints
- Moonshot Kimi K2 - offers Anthropic-compatible endpoints
- Other inference providers that offer Anthropic-compatible APIs

❌ **Incompatible providers:**

- OpenRouter - only offers OpenAI-compatible endpoints, not Anthropic-compatible
- OpenAI API directly - uses OpenAI protocol format
- Most inference providers that only support OpenAI-compatible formats

**Client Compatibility:**

- ✅ **Claude Code** - designed specifically for this use case
- ❌ **Other LLM coding assistants** (Cursor, Continue, Aider, etc.) - these use OpenAI-compatible protocols

If you need to use Claude models with other coding assistants through OpenRouter or other OpenAI-compatible providers, you would need a different proxy that translates between OpenAI and Anthropic protocols. Isoproxy maintains protocol fidelity and does not perform protocol translation.

## Testing

```bash
# Install development dependencies
# With uv (if available):
uv pip install -e ".[dev]"

# Or with pip:
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=isoproxy --cov-report=term-missing

# Run specific test file
pytest tests/test_proxy.py -v

# Run linting
ruff check src/ tests/

# Auto-format code
ruff format src/ tests/
```

## Production Deployment

1. Create a dedicated user:

```bash
sudo useradd -r -s /bin/false isoproxy
```

2. Create installation directory:

```bash
sudo mkdir -p /opt/isoproxy
sudo chown isoproxy:isoproxy /opt/isoproxy
```

3. Clone and install the proxy:

```bash
sudo -u isoproxy git clone https://github.com/carlosapgomes/isoproxy.git /opt/isoproxy
cd /opt/isoproxy
sudo -u isoproxy python3 -m venv .venv
sudo -u isoproxy .venv/bin/pip install .
```

4. Create configuration:

```bash
sudo mkdir -p /etc/isoproxy
sudo cp deployment/.env.example /etc/isoproxy/config.env
sudo nano /etc/isoproxy/config.env  # Edit configuration
sudo chown -R isoproxy:isoproxy /etc/isoproxy
sudo chmod 600 /etc/isoproxy/config.env
```

5. Install and start service:

```bash
sudo cp deployment/isoproxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable isoproxy
sudo systemctl start isoproxy
```

6. Check status:

```bash
sudo systemctl status isoproxy
sudo journalctl -u isoproxy -f
```

## Unix Socket Configuration (Recommended)

Isoproxy is designed primarily for Unix domain sockets when working with sandboxed environments like papercage. This provides:

- **Filesystem-level access control**: Socket permissions control access
- **Reduced attack surface**: No network exposure, even locally
- **Sandbox integration**: Perfect for papercage and other containerized environments
- **High performance**: Lower overhead than TCP sockets

### Basic Unix Socket Setup

```bash
# Create socket directory with proper permissions
sudo mkdir -p /run/isoproxy
sudo chown isoproxy:isoproxy /run/isoproxy
sudo chmod 755 /run/isoproxy

# Start with Unix socket
sudo -u isoproxy \
  env $(cat /etc/isoproxy/config.env | xargs) \
  /opt/isoproxy/.venv/bin/uvicorn isoproxy.main:app \
    --uds /run/isoproxy/isoproxy.sock \
    --workers 1
```

### Configure Papercage Access

When using with papercage, configure the sandbox to route API calls through the Unix socket:

```bash
# Inside papercage sandbox configuration
export ANTHROPIC_API_SOCKET=/run/isoproxy/isoproxy.sock
```

For testing with curl:

```bash
curl --unix-socket /run/isoproxy/isoproxy.sock \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"model": "claude-3-sonnet", "messages": [...]}' \
     http://localhost/v1/messages
```

### Integration with HTTP Proxy

Use with nginx, Apache, or other HTTP proxies:

**nginx example:**

```nginx
upstream isoproxy {
    server unix:/run/isoproxy/isoproxy.sock;
}

server {
    listen 127.0.0.1:9000;

    location /v1/messages {
        proxy_pass http://isoproxy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### systemd Service for Unix Socket

A dedicated service file is provided for Unix socket deployment:

```bash
# Install the Unix socket service
sudo cp deployment/isoproxy-socket.service /etc/systemd/system/

# Update the service file to use 'isoproxy' user (if needed)
sudo systemctl daemon-reload
sudo systemctl enable isoproxy-socket
sudo systemctl start isoproxy-socket

# Check status
sudo systemctl status isoproxy-socket
```

The socket will be available at `/run/isoproxy/isoproxy.sock` with proper permissions automatically managed by systemd's `RuntimeDirectory` directive.

## What This Proxy Does NOT Do

> **IMPORTANT**: This proxy does not attempt to make model output safe.

The proxy explicitly does **not**:

- ❌ Detect prompt injection
- ❌ Detect malicious code generation
- ❌ Prevent unsafe suggestions
- ❌ Filter tool instructions
- ❌ Validate semantic correctness
- ❌ Enforce human approval
- ❌ Scan content for security issues
- ❌ Block potentially harmful outputs
- ❌ Interpret or modify response content
- ❌ Provide content filtering or safety guarantees

Safety in this architecture comes from:

1. **Sandboxing**: Runtime isolation of agent execution
2. **Filesystem isolation**: Controlled access to files and directories
3. **Human review**: Explicit review processes for changes
4. **Version control**: All changes tracked and reviewable
5. **Workflow constraints**: Controlled deployment and execution pipelines

## Security Notes

**Important**: This proxy must run outside any sandbox environment (like Firejail) that contains Claude Code. It should run as a dedicated user with restricted permissions and limited network access.

## Security Considerations

- **Localhost only**: By default, the proxy binds to `127.0.0.1` and is only accessible from the local machine
- **No request/response logging**: Request and response bodies are never logged by default (metadata-only logging)
- **Protocol preservation**: Upstream errors are passed through unchanged to maintain compatibility
- **Credential isolation**: API keys are never exposed to agents, loaded from secure environment variables
- **systemd hardening**: The included service file implements comprehensive security features:
  - `NoNewPrivileges`, `PrivateDevices`, `PrivateTmp` prevent privilege escalation
  - `ProtectSystem`, `ProtectHome`, `ProtectKernel*` restrict filesystem access
  - `MemoryDenyWriteExecute` prevents runtime code injection
  - `SystemCallFilter` limits available syscalls to service essentials
  - `RestrictAddressFamilies` limits network access to IPv4/IPv6
  - Resource limits (`CPUQuota`, `MemoryMax`) prevent resource exhaustion
- **Protocol allowlisting**: Application-level endpoint validation ensures connections only to configured providers
- **API key isolation**: API keys are loaded from a secure config file (`/etc/isoproxy/config.env`) with 600 permissions, never exposed in process environment or systemd metadata
- **Unix socket support**: Can bind to Unix domain sockets for integration with other services or additional security isolation
- **Segregated execution**: Designed to run as a dedicated unprivileged user outside sandboxed environments

## Architecture

```
┌──────────────┐
│ Claude Code  │
│  (Sandbox)   │
└──────┬───────┘
       │ POST /v1/messages
       │ http://127.0.0.1:9000
       ▼
┌──────────────┐
│  Isoproxy    │
│ (localhost)  │
└──────┬───────┘
       │ POST /v1/messages
       │ https://api.anthropic.com
       ▼
┌──────────────┐
│   Upstream   │
│  Provider    │
└──────────────┘
```

## API

### Supported Endpoints

- `POST /v1/messages`: Forward request to upstream provider (preserves all fields including streaming)
- `GET /health`: Basic health check endpoint

### Unsupported

- All other routes (return 404 with "Endpoint not allowed")
- Arbitrary URL forwarding (strict allowlisting enforced)

## Troubleshooting

### Proxy won't start

- Check environment variables are set correctly
- Verify Python version is 3.11+
- Check port 9000 is not already in use: `lsof -i :9000`

### Connection refused from Claude Code

- Verify proxy is running: `curl http://127.0.0.1:9000/v1/messages`
- Check firewall rules allow localhost connections
- Ensure `ANTHROPIC_API_BASE` is set correctly in sandbox

### Upstream errors

- Check `PROXY_PROVIDER` is set correctly
- Verify the correct API key environment variable is set (e.g., `ANTHROPIC_API_KEY`)
- Check network connectivity to upstream provider
- Review logs: `journalctl -u isoproxy -f`

## Development

### Project Structure

```
isoproxy/
├── src/isoproxy/
│   ├── __init__.py       # Package metadata
│   ├── main.py           # FastAPI application (safe pass-through)
│   ├── config.py         # Configuration management
│   ├── models.py         # Minimal models (error types only)
│   ├── proxy.py          # Safe forwarding logic
│   └── errors.py         # Error handling
├── tests/                # Test suite
├── deployment/           # Deployment files
├── docs/                 # Design documentation
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

### Adding Features

This proxy is intentionally minimal and follows the safe pass-through design. Before adding features, consider if they align with the design principles documented in `docs/safe-pass-through-design.md`.

The proxy should remain:

- Boring and predictable
- Transparent (no semantic filtering)
- Hard to misuse by accident
- Focused on transport, limits, credentials, and protocol fidelity

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Attribution

This project was developed with AI assistance:

- Initial specification (`specs.md`) was written by ChatGPT (OpenAI)
- Implementation, architecture, test suite, and documentation were generated by Claude Code (Anthropic)

## Appendix: Optional Defense-in-Depth Measures

The following configuration is **not required** for isoproxy to function safely. The architecture does not rely on firewall rules for correctness or safety, as endpoint allowlisting is implemented at the application level.

These examples are provided as optional hardening steps that may help with:

- **Limiting blast radius** of potential proxy bugs (misconfigured redirects, dynamic URL handling)
- **Reducing impact** of accidental misconfiguration or typos
- **Additional guardrails** during development and experimentation

Users who prefer simpler setups can omit firewall configuration without breaking the proxy functionality.

### Optional Network Egress Filtering

If you want additional network-level restrictions, you can use the provided nftables configuration:

```bash
# Get isoproxy user ID
id -u isoproxy

# Edit the config and update ISOPROXY_UID with the actual UID
sudo nano deployment/nftables-isoproxy.conf

# Deploy the nftables rules
sudo mkdir -p /etc/nftables.d
sudo cp deployment/nftables-isoproxy.conf /etc/nftables.d/isoproxy.conf
echo 'include "/etc/nftables.d/isoproxy.conf"' | sudo tee -a /etc/nftables.conf
sudo nft -f /etc/nftables.conf

# Verify rules are active
sudo nft list ruleset | grep isoproxy

# Monitor blocked attempts (optional)
sudo journalctl -kf | grep isoproxy-blocked
```

This configuration:

- Restricts the `isoproxy` user to DNS and HTTPS traffic only
- Logs blocked connection attempts for monitoring
- Does not affect other users on the system

## Contributing

Contributions are welcome! Please ensure:

- All tests pass: `pytest`
- Code is formatted: `ruff format`
- No linting errors: `ruff check`
- New features include tests
- Security considerations are documented
