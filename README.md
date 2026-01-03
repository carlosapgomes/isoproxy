# Isoproxy

**Minimal Anthropic-compatible proxy for Claude Code**

Isoproxy is a lightweight HTTP proxy server that forwards Claude Code requests to a configurable Anthropic-compatible API endpoint. It enables Claude Code to run in a sandboxed environment while securely accessing the API through a trusted proxy that holds the API credentials.

## Features

- **Minimal attack surface**: Only supports `POST /v1/messages`
- **Configurable upstream**: Works with Anthropic or any compatible API provider
- **Model override**: Optionally force all requests to use a specific model
- **Security-first**: Error normalization prevents information leakage, no request/response body logging, localhost-only binding by default
- **Segregated deployment**: Designed to run outside sandboxed environments (Firejail, etc.) as the only controlled egress point
- **Simple deployment**: Single Python process, systemd service included
- **Well-tested**: Comprehensive test suite with pytest (95% coverage)

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

```bash
# Set required environment variables
export PROXY_UPSTREAM_BASE=https://api.anthropic.com
export PROXY_API_KEY=sk-ant-your-api-key-here

# Optional: Override model for all requests
# export PROXY_DEFAULT_MODEL=claude-3-5-sonnet-20241022

# Optional: Set timeout (default: 30 seconds)
# export PROXY_TIMEOUT=60
```

Alternatively, copy `deployment/.env.example` to `.env` and fill in your values:

```bash
cp deployment/.env.example .env
# Edit .env with your favorite editor
```

### 3. Run the Proxy

```bash
# Development mode (with auto-reload)
uvicorn isoproxy.main:app --reload --host 127.0.0.1 --port 9000

# Production mode
uvicorn isoproxy.main:app --host 127.0.0.1 --port 9000 --workers 1
```

### 4. Configure Claude Code

In your Claude Code sandbox environment:

```bash
export ANTHROPIC_API_BASE=http://127.0.0.1:9000
export ANTHROPIC_API_KEY=dummy  # Ignored by proxy
```

Claude Code will now use the proxy to access the upstream API.

## Configuration Reference

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `PROXY_UPSTREAM_BASE` | Yes | - | Base URL of upstream API (e.g., `https://api.anthropic.com`) |
| `PROXY_API_KEY` | Yes | - | API key for upstream authentication |
| `PROXY_DEFAULT_MODEL` | No | `None` | Force all requests to use this model |
| `PROXY_TIMEOUT` | No | `30` | Timeout for upstream requests (1-300 seconds) |
| `PROXY_HOST` | No | `127.0.0.1` | Host to bind proxy server to |
| `PROXY_PORT` | No | `9000` | Port to bind proxy server to |

## Testing

```bash
# Install development dependencies
uv pip install -e ".[dev]"

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

### Using systemd

1. Create a dedicated user:

```bash
sudo useradd -r -s /bin/false llmproxy
```

2. Install the proxy:

```bash
sudo mkdir -p /opt/isoproxy
sudo cp -r . /opt/isoproxy/
cd /opt/isoproxy
sudo uv venv
sudo uv pip install .
```

3. Create configuration:

```bash
sudo mkdir -p /etc/isoproxy
sudo cp deployment/.env.example /etc/isoproxy/config.env
sudo nano /etc/isoproxy/config.env  # Edit configuration
sudo chown -R llmproxy:llmproxy /etc/isoproxy
sudo chmod 600 /etc/isoproxy/config.env
```

4. Install and start service:

```bash
sudo cp deployment/isoproxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable isoproxy
sudo systemctl start isoproxy
```

5. Check status:

```bash
sudo systemctl status isoproxy
sudo journalctl -u isoproxy -f
```

## Running in a Segregated Environment

**This proxy must not run inside the same sandbox as the agent (Claude Code).**
It is designed to run outside the sandbox and act as the only controlled egress point.

### 1. Execution Model (Important)

**Claude Code (agent) runs:**
- Inside Firejail (or equivalent)
- With no internet access
- With `net lo` only

**isoproxy runs:**
- Outside Firejail
- As a separate UNIX user
- With restricted outbound internet access
- Bound to `127.0.0.1` only

**This separation is mandatory.**

### 2. Create a Dedicated User (Host)

```bash
sudo useradd \
  --system \
  --no-create-home \
  --shell /usr/sbin/nologin \
  llmproxy
```

This user will own and run the proxy.

### 3. Install and Configure the Proxy

#### 3.1 Clone the repository

```bash
sudo -u llmproxy git clone https://github.com/carlosapgomes/isoproxy.git /opt/isoproxy
cd /opt/isoproxy
```

#### 3.2 Create a Python environment

```bash
sudo -u llmproxy python3 -m venv /opt/isoproxy/venv
sudo -u llmproxy /opt/isoproxy/venv/bin/pip install -e .
```

(Adjust if you are using `uv` or another tool.)

### 4. Configure Environment Variables

Create a file readable only by `llmproxy`:

```bash
sudo -u llmproxy nano /opt/isoproxy/env
```

Example:

```bash
PROXY_UPSTREAM_BASE=https://api.anthropic.com
PROXY_API_KEY=sk-ant-xxxxxxxx
PROXY_DEFAULT_MODEL=claude-3-5-sonnet-20241022
PROXY_TIMEOUT=30
```

Set permissions:

```bash
sudo chmod 600 /opt/isoproxy/env
sudo chown llmproxy:llmproxy /opt/isoproxy/env
```

### 5. Start the Proxy (Manual)

```bash
sudo -u llmproxy \
  env $(cat /opt/isoproxy/env | xargs) \
  /opt/isoproxy/venv/bin/uvicorn isoproxy.main:app \
    --host 127.0.0.1 \
    --port 9000
```

You should now have `http://127.0.0.1:9000/v1/messages` available locally.

### 6. Firewall (Strongly Recommended)

Restrict outbound access for `llmproxy` using the included nftables configuration:

```bash
# Get llmproxy user ID
id -u llmproxy

# Edit the config and update LLMPROXY_UID with the actual UID
sudo nano deployment/nftables-llmproxy.conf

# Deploy the nftables rules
sudo mkdir -p /etc/nftables.d
sudo cp deployment/nftables-llmproxy.conf /etc/nftables.d/llmproxy.conf
echo 'include "/etc/nftables.d/llmproxy.conf"' | sudo tee -a /etc/nftables.conf

# Load the rules
sudo nft -f /etc/nftables.conf

# Verify
sudo nft list ruleset | grep llmproxy
```

This restricts `llmproxy` to:
- ✅ Loopback (for binding to 127.0.0.1:9000)
- ✅ DNS (for resolving upstream hostname)
- ✅ HTTPS (for connecting to upstream API)
- ❌ Everything else is logged and blocked

Monitor blocked attempts:
```bash
sudo journalctl -kf | grep llmproxy-blocked
```

### 7. Configure Claude Code (Sandbox)

Inside the Firejail sandbox:

```bash
export ANTHROPIC_API_BASE=http://127.0.0.1:9000
export ANTHROPIC_API_KEY=dummy
```

Then run:

```bash
claude
```

Claude Code will connect only to the local proxy.

### 8. Verify Isolation

**Inside the sandbox:**

```bash
curl http://127.0.0.1:9000/v1/messages  # should connect to proxy
curl https://api.anthropic.com          # must FAIL
```

**Outside the sandbox:**

```bash
curl http://127.0.0.1:9000/v1/messages  # should work
```

### 9. What Not To Do (Explicit)

- ❌ Do not run the proxy inside Firejail
- ❌ Do not bind to `0.0.0.0`
- ❌ Do not give the agent internet access
- ❌ Do not store API keys in the sandbox
- ❌ Do not log request/response bodies

### 10. Why This Matters

This proxy exists to move trust and secrets outside the agent while still allowing Claude Code to function. Running it outside the sandbox and restricting it at the OS level ensures that even if the agent is compromised, it cannot access the internet, API keys, or other system resources directly.

## Security Considerations

- **Localhost only**: By default, the proxy binds to `127.0.0.1` and is only accessible from the local machine
- **No request/response logging**: Request and response bodies are never logged to prevent data leakage
- **Error normalization**: All upstream errors (4xx/5xx) are normalized to prevent information leakage:
  - Status codes are preserved for functional behavior (retry/backoff logic)
  - Error messages are sanitized to hide provider-specific details
  - Rate limit numbers, error taxonomy, and other sensitive details are stripped
  - Network/timeout errors return generic 502 responses
- **systemd hardening**: The included service file implements comprehensive security features:
  - `NoNewPrivileges`, `PrivateDevices`, `PrivateTmp` prevent privilege escalation
  - `ProtectSystem`, `ProtectHome`, `ProtectKernel*` restrict filesystem access
  - `MemoryDenyWriteExecute` prevents runtime code injection
  - `SystemCallFilter` limits available syscalls to service essentials
  - `RestrictAddressFamilies` limits network access to IPv4/IPv6
  - Resource limits (`CPUQuota`, `MemoryMax`) prevent resource exhaustion
- **Network egress filtering**: Optional nftables configuration (`deployment/nftables-llmproxy.conf`) restricts outbound connections:
  - User-scoped filtering (only affects `llmproxy` user)
  - Allows only loopback, DNS, and HTTPS
  - Logs all blocked connection attempts for monitoring
  - Prevents exfiltration via HTTP, FTP, SSH, or other protocols
- **API key isolation**: API keys are loaded from a secure config file (`/etc/isoproxy/config.env`) with 600 permissions, never exposed in process environment or systemd metadata
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

### Supported Endpoint

- `POST /v1/messages`: Forward request to upstream Anthropic Messages API

### Unsupported

- Streaming (`stream: true` is rejected with 422)
- All other routes (return 404)
- Tools/function calling
- Any modifications to request/response bodies

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

- Check `PROXY_UPSTREAM_BASE` is correct
- Verify `PROXY_API_KEY` is valid
- Check network connectivity to upstream
- Review logs: `journalctl -u isoproxy -f`

## Development

### Project Structure

```
isoproxy/
├── src/isoproxy/
│   ├── __init__.py       # Package metadata
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration management
│   ├── models.py         # Pydantic models
│   ├── validation.py     # Request processing
│   ├── proxy.py          # Upstream forwarding
│   └── errors.py         # Error handling
├── tests/                # Test suite
├── deployment/           # Deployment files
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

### Adding Features

This proxy is intentionally minimal. Before adding features, consider if they align with the security model documented in `specs.md`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Attribution

This project was developed with AI assistance:
- Initial specification (`specs.md`) was written by ChatGPT (OpenAI)
- Implementation, architecture, test suite, and documentation were generated by Claude Code (Anthropic)

## Contributing

Contributions are welcome! Please ensure:

- All tests pass: `pytest`
- Code is formatted: `ruff format`
- No linting errors: `ruff check`
- New features include tests
- Security considerations are documented
