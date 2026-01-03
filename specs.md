---

# Minimal Anthropic-Compatible Proxy Specification

(**Configurable Upstream Endpoint**)

## 1. Purpose

Provide a **local HTTP proxy** that implements the **minimum subset** of the Anthropic Messages API required by **Claude Code**, while allowing the upstream API endpoint to be **configurable** (to support Anthropic-compatible providers).

---

## 2. Deployment Model

### 2.1 Process

* Long-running HTTP server
* Runs **outside** the sandbox
* Runs as **unprivileged UNIX user** (e.g. `llmproxy`)
* Single process, no workers

---

### 2.2 Network Binding

* Listens **only** on:

  ```
  127.0.0.1:9000
  ```
* Must not bind to external interfaces

---

## 3. Configuration (Environment Variables)

### Required

```bash
PROXY_UPSTREAM_BASE=https://api.anthropic.com
PROXY_API_KEY=sk-...
```

Where:

* `PROXY_UPSTREAM_BASE` is the **base URL** of an Anthropic-compatible API

  * Example:

    * `https://api.anthropic.com`
    * `https://my-provider.example.com`
* The proxy appends `/v1/messages` internally

---

### Optional

```bash
PROXY_DEFAULT_MODEL=claude-3-5-sonnet
PROXY_TIMEOUT=30
```

---

## 4. Supported HTTP Interface

### 4.1 Local Endpoint (Inbound)

```
POST /v1/messages
```

No other routes are supported.

---

## 5. Request Handling

### 5.1 Accepted Payload

The proxy accepts requests conforming to Anthropic’s Messages API.

Minimal required fields:

```json
{
  "model": "string",
  "messages": [
    { "role": "user", "content": "string" }
  ],
  "max_tokens": 1024
}
```

---

### 5.2 Validation Rules

The proxy must:

* Reject non-POST requests
* Reject invalid JSON
* Reject missing `messages`
* Reject `"stream": true`
* Ignore any client-supplied API key
* Optionally override `model` if `PROXY_DEFAULT_MODEL` is set

---

## 6. Upstream Forwarding

### 6.1 Upstream URL Construction

The proxy constructs the upstream URL as:

```
{PROXY_UPSTREAM_BASE}/v1/messages
```

No other upstream paths are allowed.

---

### 6.2 Upstream Request

* Method: `POST`
* Headers:

  ```
  Content-Type: application/json
  Authorization: Bearer $PROXY_API_KEY
  ```
* Body:

  * Original request body
  * Possibly modified `model` field

---

## 7. Response Handling

### 7.1 Success

* Return upstream response **verbatim**
* Preserve:

  * HTTP status
  * JSON body
  * Content-Type

Claude Code expects native Anthropic responses.

---

### 7.2 Failure

On proxy-side failure:

HTTP `502`

```json
{
  "type": "error",
  "error": {
    "type": "proxy_error",
    "message": "Upstream request failed"
  }
}
```

No upstream error bodies are leaked.

---

## 8. Explicit Constraints

The proxy must **not**:

* Support streaming
* Support tools or function calling
* Accept arbitrary URLs
* Expose health endpoints
* Log request or response bodies
* Read or write files
* Execute shell commands

---

## 9. Security Model (Minimal)

* Agent:

  * No internet
  * No secrets
* Proxy:

  * Holds API key
  * Has limited outbound HTTPS
* Network boundary enforced by host (Firejail + nftables)

---

## 10. Claude Code Configuration

Inside the sandbox:

```bash
export ANTHROPIC_API_BASE=http://127.0.0.1:9000
export ANTHROPIC_API_KEY=dummy
```

Claude Code will transparently use the proxy.

---

## 11. Expected Runtime Flow

```
Claude Code
   |
   | POST /v1/messages
   v
Local Proxy (127.0.0.1)
   |
   | POST {PROXY_UPSTREAM_BASE}/v1/messages
   v
Upstream Provider
```

---

## 12. Non-Goals (Explicit)

This proxy does **not** attempt to:

* sanitize prompts
* sanitize outputs
* enforce budgets
* provide audit logs
* multiplex providers
* implement MCP semantics

---

## 13. Design Principle

> **This proxy exists solely to relocate trust and secrets outside the agent.**

Everything else is deliberately excluded.

---

