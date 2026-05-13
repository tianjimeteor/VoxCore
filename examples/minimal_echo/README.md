# Minimal Echo

The simplest VoxCore app. No API keys, no external services. Use it to verify
your setup before wiring real providers.

```bash
pip install -e ".[dev]"
python -m voxcore.cli gen-secret > .env
python examples/minimal_echo/app.py
```

Then open `examples/web_demo/index.html` in a browser, log in with any user
you register through the REST API, and start typing.
