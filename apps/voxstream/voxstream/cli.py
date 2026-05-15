"""voxstream — command-line interface.

Examples::

    voxstream run                      # default: echo ASR, port 7860
    voxstream run --asr xunfei
    voxstream run --translate zh
    voxstream check                    # probe audio backends
    voxstream open-overlay             # print URL + open browser
"""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from typing import Sequence

from . import __version__
from .capture import probe
from .server import create_app


def _cmd_run(args: argparse.Namespace) -> int:
    import uvicorn

    app = create_app(asr=args.asr, translate_to=args.translate)
    print(f"VoxStream {__version__} running on http://{args.host}:{args.port}")
    print(f"Add this URL as an OBS Browser Source:")
    print(f"   http://{args.host}:{args.port}/overlay?theme={args.theme}")
    if args.translate:
        print(f"Translation enabled: -> {args.translate}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _cmd_check(_args: argparse.Namespace) -> int:
    print(json.dumps(probe(), indent=2, default=str))
    return 0


def _cmd_open_overlay(args: argparse.Namespace) -> int:
    url = f"http://localhost:{args.port}/overlay?theme={args.theme}"
    print(url)
    if not args.no_open:
        webbrowser.open(url)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="voxstream", description="OBS Browser Source live captions powered by VoxCore.")
    p.add_argument("--version", action="version", version=f"voxstream {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Start the caption server.")
    pr.add_argument("--host", default="127.0.0.1")
    pr.add_argument("--port", type=int, default=7860)
    pr.add_argument("--asr", default="echo", help="Adapter name registered with voxcore.adapters.asr")
    pr.add_argument("--translate", default=None, help="ISO code, e.g. zh / en / ja. Off when omitted.")
    pr.add_argument("--theme", default="streaming", choices=["streaming", "classroom", "meeting", "minimal"])
    pr.set_defaults(func=_cmd_run)

    pc = sub.add_parser("check", help="Print audio backend diagnostics.")
    pc.set_defaults(func=_cmd_check)

    po = sub.add_parser("open-overlay", help="Print the overlay URL and open it in the default browser.")
    po.add_argument("--port", type=int, default=7860)
    po.add_argument("--theme", default="streaming")
    po.add_argument("--no-open", action="store_true")
    po.set_defaults(func=_cmd_open_overlay)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
