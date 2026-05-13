# Voice Assistant

Realistic single-file example: echo ASR (swap for `xunfei` once you have
credentials), DeepSeek LLM, concise system prompt.

```bash
cp .env.example .env
# fill DEEPSEEK_API_KEY
python -m voxcore.cli gen-secret >> .env    # add JWT_SECRET_KEY
python examples/voice_assistant/app.py
```
