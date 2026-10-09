# Learning Companion Chatbot

A small local app that lets Open WebUI chat with Grok through a LangChain Learning Companion prompt.

```
Open WebUI → this app (/v1/chat/completions) → LangChain prompt + Grok → answer in Open WebUI
```

## Setup

Needs Python 3.12 and `uv`.

```bash
uv sync
cp .env.example .env
```

Edit `.env`:

- `GROK_API_KEY` — your own xAI (Grok) API key. Put it only in `.env`; that file is never committed.
- `GROK_MODEL_NAME` — the model name your instructor gives you.

## Run

```bash
uv run learning-companion     # starts on http://127.0.0.1:8000
```

Check it in a second terminal:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models
```

## Connect Open WebUI

Do not reinstall or change Open WebUI itself — just add a connection in its settings:

- **Base URL:** `http://127.0.0.1:8000/v1`
  (if your Open WebUI runs in Docker, use `http://host.docker.internal:8000/v1`)
- **API key:** any placeholder text, e.g. `local`. Your real key stays in `.env`.
- **Model:** pick the value of `GROK_MODEL_NAME`.

If the key or model name is missing, the chat shows a clear configuration message instead of crashing.

## Lint and test

```bash
uv run ruff format src tests
uv run ruff check --fix src tests
uv run pytest
```
