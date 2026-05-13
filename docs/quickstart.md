# Quickstart

## Install

```bash
pip install voxcore            # latest release
# or, from source
git clone https://github.com/tianjimeteor/VoxCore.git
cd voxcore
pip install -e ".[dev]"
```

## First run (no credentials)

```bash
python -m voxcore.cli gen-secret > .env
voxcore run --asr echo --llm echo
```

Open `http://localhost:8000/docs` — FastAPI's auto-generated docs — to explore
the REST endpoints. For the WebSocket gateway, use `examples/web_demo/index.html`.

## Real providers

Add to `.env`:

```ini
DEEPSEEK_API_KEY=sk-...
```

Then:

```bash
voxcore run --asr echo --llm deepseek
```

## Writing your own app

```python
# app.py
from voxcore import VoxCore

app = VoxCore(asr="echo", llm="deepseek")

@app.on_transcript
async def handler(text, ctx):
    async for chunk in ctx.llm.complete(f"Answer briefly: {text}"):
        await ctx.send(chunk)

if __name__ == "__main__":
    app.run()
```

Run with `python app.py` or deploy with `uvicorn app:app.app --workers 4`.
