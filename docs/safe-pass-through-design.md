# Safe Pass-Through Design

## What This Proxy Does

Isoproxy implements a **safe pass-through** proxy designed for sandboxed environments (especially [papercage](https://github.com/carlosapgomes/papercage)) with these characteristics:

- **Strict endpoint allowlisting**: Only forwards to configured provider endpoints
- **Protocol preservation**: Forwards unknown fields unchanged to maintain API compatibility
- **Resource boundaries**: Enforces request/response size limits and timeouts
- **Credential isolation**: Injects API keys securely, agent never sees credentials
- **Transparent operation**: Minimal semantic interpretation of requests/responses
- **Unix domain socket support**: Designed for sandboxed environments like papercage

## What This Proxy Explicitly Does NOT Do

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

## Where Safety Actually Comes From

In this architecture, safety is provided by:

1. **Sandboxing**: Runtime isolation of agent execution (e.g., papercage)
2. **Filesystem isolation**: Controlled access to files and directories
3. **Network isolation**: Unix domain sockets prevent direct network access
4. **Human review**: Explicit review processes for changes
5. **Version control**: All changes tracked and reviewable
6. **Workflow constraints**: Controlled deployment and execution pipelines

## Design Philosophy

> The proxy's role is to be **boring, predictable, and hard to misuse by accident**.

This proxy is **intentionally dull** - it focuses on:

- Reliable transport
- Resource limits
- Credential security
- Protocol fidelity

It explicitly avoids:

- Content analysis
- Semantic filtering
- "Smart" behavior
- Heuristic decisions

## Configuration Boundaries

The proxy enforces these strict boundaries:

### Transport & Endpoint Control ✅

- Only connects to explicit provider allowlist
- No DNS resolution controlled by agent input
- No arbitrary URL forwarding
- HTTPS required

### Credential Handling ✅

- API keys injected by proxy, never forwarded from agent
- Agent cannot read, write, or influence credentials
- Per-provider credential isolation
- Credentials never appear in logs

### Request Size & Shape Limits ✅

- Maximum request body size enforced
- Maximum response body size enforced
- Timeouts enforced on upstream calls
- Streaming responses bounded by time and size

### Protocol Preservation ✅

- Anthropic-compatible JSON fields forwarded verbatim
- Unknown fields passed through (not stripped)
- Provider-specific extensions preserved
- Streaming semantics preserved exactly

## Trust Boundaries

- **Model**: Untrusted
- **Agent**: Constrained elsewhere (not by this proxy)
- **Proxy**: Network chokepoint and protocol steward only
- **Safety**: Provided by external systems (sandboxing, review, etc.)

This proxy is **not** an authorization boundary, policy engine, or security filter.

