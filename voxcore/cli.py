"""Command-line interface: ``voxcore run`` / ``voxcore gen-secret``."""
from __future__ import annotations

import secrets

import click


@click.group()
@click.version_option(package_name="voxcore")
def main() -> None:
    """VoxCore command-line utilities."""


@main.command("gen-secret")
@click.option("--bytes", "n_bytes", default=48, show_default=True, help="Secret strength.")
def gen_secret(n_bytes: int) -> None:
    """Print a fresh JWT secret suitable for ``JWT_SECRET_KEY=``."""
    click.echo(f"JWT_SECRET_KEY={secrets.token_urlsafe(n_bytes)}")


@main.command("run")
@click.option("--asr", default="echo", show_default=True)
@click.option("--llm", default="echo", show_default=True)
@click.option("--host", default=None)
@click.option("--port", default=None, type=int)
def run(asr: str, llm: str, host: str | None, port: int | None) -> None:
    """Start VoxCore with the chosen adapters. Good for kicking the tires.

    For real apps, write your own ``app.py`` that constructs ``VoxCore(...)``
    and register your ``@app.on_transcript`` handlers.
    """
    from . import VoxCore

    app = VoxCore(asr=asr, llm=llm)

    @app.on_transcript
    async def default(text: str, ctx) -> None:  # type: ignore[no-untyped-def]
        if ctx.llm is None:
            await ctx.send(f"[no llm configured] got: {text}")
            return
        async for chunk in ctx.llm.complete(text):
            await ctx.send(chunk)

    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
