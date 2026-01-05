# Isoproxy: Safe Pass-Through Proxy Design Guide

**Status:** Design guidance  
**Audience:** Developers refactoring `isoproxy`  
**Scope:** Proxy behavior only (not sandboxing, git workflow, or agent orchestration)

---

## 0. Intent and Non-Intent

### Intent

This document defines the minimum required behaviors for running `isoproxy` in
**safe pass-through mode** when used with:

- Claude Code (interactive or headless)
- Anthropic’s native API
- Anthropic-compatible inference providers
- Providers that auto-map models and negotiate context windows dynamically

The goal is to:

- Preserve protocol fidelity
- Avoid breaking Claude’s inference loop
- Avoid semantic filtering or rewriting
- Reduce accidental risk introduced by the proxy itself

### Non-Intent

This document does **not** attempt to:

- Secure or sanitize model output
- Detect prompt injection
- Enforce content or safety policy
- Interpret model intent
- Validate tool instructions
- Replace sandboxing or human review

Those concerns are intentionally handled elsewhere in the system.

---

## 1. Threat Model (Explicitly Limited)

This proxy assumes:

- The model is untrusted
- The agent is constrained via sandboxing and workflow gates
- The proxy is not a policy engine
- The proxy is not an IDS/IPS
- The proxy is not an authorization boundary for actions

The proxy is a **network chokepoint and protocol steward**, nothing more.

---

## 2. Definition: “Safe Pass-Through”

**Safe pass-through** means:

> Requests and responses are forwarded without semantic inspection or modification,
> while enforcing strict structural, transport, and resource boundaries.

This creates a system that is:

- Predictable
- Debuggable
- Compatible with multiple providers
- Resistant to accidental misuse
- Honest about what it does _not_ protect against

---

## 3. Minimal “Safe Pass-Through” Checklist

This checklist defines the minimum acceptable baseline.

### 3.1 Transport & Endpoint Control (MUST)

- Proxy connects only to an explicit allowlist of upstream endpoints
- No agent-controlled DNS resolution
- No arbitrary URL forwarding
- HTTPS only (no plaintext fallback)

**Rationale:** Prevents the proxy from becoming a generic exfiltration tunnel.

---

### 3.2 Credential Handling (MUST)

- API keys are injected by the proxy
- Credentials never pass through the agent
- Per-provider credential isolation
- Credentials never appear in logs (including debug)

**Rationale:** Credentials are the proxy’s most sensitive asset.

---

### 3.3 Request Size & Shape Limits (MUST)

- Maximum request body size enforced
- Maximum response body size enforced
- Upstream request timeouts enforced
- Streaming responses bounded by time and size

**Rationale:** Prevents memory exhaustion and denial-of-service via the proxy.

---

### 3.4 Protocol Preservation (MUST)

- Anthropic-compatible JSON fields forwarded verbatim
- Unknown fields preserved, not stripped
- Provider-specific extensions preserved
- Streaming semantics preserved exactly

**Rationale:** Claude Code and providers may rely on evolving or undocumented fields.

---

### 3.5 Model & Context Negotiation Transparency (MUST)

- No hardcoded context window assumptions
- No token accounting or correction
- Provider error messages passed through unchanged
- Model remapping left to providers

**Rationale:** Auto-mapped models and context sizes must remain a provider concern.

---

### 3.6 Logging Discipline (MUST)

- Logging is configurable
- No prompt or response content logged by default
- Metadata-only logging supported
- Debug logging explicitly opt-in

**Rationale:** Logs are a secondary data leak vector.

---

## 4. What Must Always Remain Enabled (Even in Pass-Through)

These responsibilities are non-negotiable.

### 4.1 Endpoint Allowlisting

The proxy must never become a general forward proxy.

- Explicit provider configuration
- No user-supplied URLs
- Fail closed on misconfiguration

---

### 4.2 Credential Boundary

The agent:

- Never supplies credentials
- Never sees credentials
- Never influences which credential is used beyond provider selection

This boundary must not be bypassable.

---

### 4.3 Resource Limits

At minimum:

- Request size limits
- Response size limits
- Timeouts

Without these, pass-through becomes unsafe by accident.

---

### 4.4 Protocol Fidelity Over Cleverness

The proxy should prefer:

> “Forward unknown fields untouched”

over:

> “Normalize, sanitize, or reinterpret”

Breaking the inference loop is worse than passing unexpected fields.

---

### 4.5 Deterministic Behavior

Given the same request and upstream behavior:

- The proxy behaves identically
- No heuristic rewriting
- No adaptive filtering

Determinism matters more than “helpfulness”.

---

## 5. Explicitly Out of Scope (Document This Clearly)

The proxy does not:

- Detect prompt injection
- Detect malicious code generation
- Prevent unsafe suggestions
- Filter tool instructions
- Enforce human approval

These concerns are handled by sandboxing, review gates, and workflow design.

---

## 6. Refactoring Guidance for Isoproxy

When refactoring, prefer **removal** over addition.

### Remove or Avoid

- Semantic filters
- Content rewriting
- Model-specific assumptions
- Token counting logic
- “Smart” error interpretation

### Keep or Add

- Strict size and timeout guards
- Clear configuration schema
- Minimal provider abstraction
- Fail-closed behavior
- Clear separation of debug vs production modes

---

## 7. Recommended Configuration Shape

```yaml
providers:
  anthropic:
    endpoint: https://api.anthropic.com
    api_key_env: ANTHROPIC_API_KEY

  openrouter:
    endpoint: https://openrouter.ai/api/anthropic
    api_key_env: OPENROUTER_API_KEY

limits:
  max_request_bytes: 5MB
  max_response_bytes: 20MB
  timeout_seconds: 120

logging:
  mode: metadata # off | metadata | debug

```
