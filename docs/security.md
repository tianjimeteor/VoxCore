# Security Model

VoxCore's security posture rests on four principles:

1. **Fail closed by default.** Insecure configurations abort at startup.
2. **Boundary validation only.** Trust internal code; verify at HTTP / WebSocket edges.
3. **Audit without side-channels.** Security events are observable but error
   responses never leak implementation details (e.g., user enumeration).
4. **Extension over modification.** Hooks (`AuditHook`, `BillingHook`) are the
   supported way to layer custom policy.

## Built-in protections

| Attack                            | Mitigation                                             |
| --------------------------------- | ------------------------------------------------------ |
| Default/weak JWT secret           | Startup validator rejects placeholders + short keys    |
| CORS wildcard misconfiguration    | Defaults to localhost; production must set origins     |
| SQL injection                     | SQLAlchemy ORM; no raw string SQL in the codebase      |
| Password brute force              | `check_rate_limit("login")` with 10 attempts / 5 min   |
| Registration flood                | `check_rate_limit("register")` with 5 attempts / 5 min |
| Username enumeration on login     | Identical error for unknown user vs wrong password     |
| WebSocket unauthenticated access  | JWT required via `?token=`; closes 1008 otherwise      |
| WebSocket DoS via huge frames     | `ws_max_message_bytes` (default 1 MB) per frame        |
| Idle WebSocket exhaustion         | `ws_heartbeat_seconds` (default 60 s) receive timeout  |
| Dependency CVEs                   | `pip-audit` + Dependabot weekly                        |
| Secrets committed to repo         | `gitleaks` on every PR                                 |
| Insecure deserialization          | Only `WebSocket.receive_json()`; no `pickle` anywhere  |

## Threat model boundaries

VoxCore is **not** responsible for:

- TLS termination — run behind a reverse proxy (Caddy, nginx, Cloudflare)
- DDoS at the L4/L7 edge — use a dedicated WAF/CDN
- Host-level hardening (seccomp, AppArmor) — see `docker-compose.yml` for
  starting points
- Upstream-provider data handling (Xunfei, OpenAI etc. see their own policies)

## Disclosure

See [SECURITY.md](../SECURITY.md) in the repo root.
