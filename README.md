# Isoproxy

**Minimal Anthropic-compatible proxy for Claude Code**

Isoproxy is a lightweight HTTP proxy server that forwards Claude Code requests to a configurable Anthropic-compatible API endpoint. It enables Claude Code to run in a sandboxed environment while securely accessing the API through a trusted proxy that holds the API credentials.

## Features

- **Minimal attack surface**: Only supports `POST /v1/messages`
- **Configurable upstream**: Works with Anthropic or any compatible API provider
- **Model override**: Optionally force all requests to use a specific model
- **Security-first**: No request/response body logging, localhost-only binding by default
- **Simple deployment**: Single Python process, systemd service included
- **Well-tested**: Comprehensive test suite with pytest

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

## Security Considerations

- **Localhost only**: By default, the proxy binds to `127.0.0.1` and is only accessible from the local machine
- **No request/response logging**: Request and response bodies are never logged to prevent data leakage
- **Generic error responses**: Upstream errors are not leaked to clients (returns generic 502)
- **systemd hardening**: The included service file uses security features like `NoNewPrivileges`, `ProtectSystem`, etc.
- **API key isolation**: The proxy holds the API key, while the sandboxed agent has no access to secrets

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
