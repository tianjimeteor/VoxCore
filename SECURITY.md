# Security Policy

## Supported Versions

We provide security fixes for the following versions:

| Version | Supported |
| ------- | --------- |
| latest  | Yes       |
| 0.x     | Best-effort until 1.0 |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security problems.**

Use GitHub's private vulnerability reporting:
[Report a vulnerability](https://github.com/tianjimeteor/VoxCore/security/advisories/new)

Include:

- A description of the vulnerability
- Steps to reproduce or a proof-of-concept
- The impact you foresee
- Your name/handle for acknowledgement (optional)

We commit to:

1. Acknowledging your report within **72 hours**
2. Providing an initial assessment within **7 days**
3. Coordinating a fix and disclosure within **90 days** of your report

You will be credited in the advisory unless you prefer to remain anonymous.

## Hardening Checklist (operators)

Running VoxCore in production? At minimum:

- [ ] Generate a strong `JWT_SECRET_KEY` (see `voxcore gen-secret`)
- [ ] Set `ALLOWED_ORIGINS` to your explicit frontend domain(s)
- [ ] Terminate TLS at your reverse proxy (Caddy / nginx / Cloudflare)
- [ ] Put the service behind an IP/WAF rate limiter in addition to built-in limits
- [ ] Rotate API keys for upstream ASR/LLM providers regularly
- [ ] Enable `AuditHook` and forward logs to your SIEM
- [ ] Run the container as a non-root user (our default Dockerfile already does)
- [ ] Pin images by digest, not by `:latest`
- [ ] Subscribe to GitHub security advisories for this repo

## Known security-relevant CI checks

Every PR runs:

- `gitleaks` (secret scanning, blocks merge on finding)
- `pip-audit` (dependency CVE scanning)
- `CodeQL` (static analysis for Python)
- `ruff` + `mypy` (type & lint)

## Safe-harbor

We will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations and service disruption
- Report the issue privately before public disclosure
- Do not exfiltrate data beyond what is needed to demonstrate the bug

Thank you for helping keep VoxCore and its users safe.
