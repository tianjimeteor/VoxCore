# Contributing to VoxCore

First off — thanks for taking the time to contribute!

## Quick links

- Found a bug? [Open an issue](https://github.com/tianjimeteor/VoxCore/issues/new?template=bug_report.yml)
- Have an idea? [Start a discussion](https://github.com/tianjimeteor/VoxCore/discussions)
- Security issue? **Do not** open a public issue — see [SECURITY.md](SECURITY.md)

## Development setup

```bash
git clone https://github.com/tianjimeteor/VoxCore.git
cd voxcore

# Install in editable mode with dev extras
pip install -e ".[dev]"

# Generate a local JWT secret
python -m voxcore.cli gen-secret > .env

# Run tests
pytest

# Run lint + type check
ruff check .
mypy voxcore
```

## Writing an adapter

Adapters are the easiest place to contribute. See [docs/adapters.md](docs/adapters.md).

Minimum viable PR for a new LLM adapter:

1. Create `voxcore/adapters/llm/<provider>.py` implementing `LLMAdapter`
2. Register it in `voxcore/adapters/llm/__init__.py`
3. Add a test under `tests/adapters/test_<provider>.py` (mock the HTTP layer — no live calls in CI)
4. Update the adapter table in `README.md`

## Pull-request checklist

- [ ] Branch from `main`, name it `feat/…`, `fix/…`, or `docs/…`
- [ ] One logical change per PR; keep it under ~400 lines of diff when possible
- [ ] Add or update tests (aim for ≥80% coverage on changed code)
- [ ] `ruff check . && mypy voxcore && pytest` all pass locally
- [ ] No hard-coded secrets or API keys — `gitleaks` runs in CI
- [ ] Update `README.md` / `docs/` if behavior changes
- [ ] Sign-off your commits (`git commit -s`) — we use [DCO](https://developercertificate.org/)

## Commit message style

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(asr): add deepgram adapter
fix(auth): reject JWT with missing `sub` claim
docs: clarify ALLOWED_ORIGINS default
```

## Code style

- Python 3.10+, typed throughout
- `ruff` is the single source of truth for formatting and linting (config in `pyproject.toml`)
- Comments explain **why**, not **what** — keep them short
- Public API docstrings should include a usage example

## Governance

VoxCore uses a BDFL-lite model: core maintainers merge, but architectural
changes require an RFC issue first. See `docs/rfcs/` for the template.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Please be kind.
