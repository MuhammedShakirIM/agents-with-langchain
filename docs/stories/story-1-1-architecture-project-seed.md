# Story 1.1 — Architecture and Project Seed

Status: Ready for implementation
Course: Beginner LangChain and LangGraph classroom course
Capstone: Learning Companion Chatbot
Project path: repository root (no `docs/config.yaml` exists)

---

## Purpose

Agree on one simple picture of the classroom app, then create the smallest working project that matches it. At the end, a participant types a question in Open WebUI and gets a Grok reply that came through our own local app.

This story has two phases with a hard stop between them:

1. **Phase A — Architecture.** Write `docs/architecture.md` and ask the instructor to approve it.
2. **Phase B — Project seed.** Only after explicit approval, create the project.

## What this story implements in plain English

After this story, a participant will be able to:

- Start the Learning Companion app on their own laptop with one command.
- Open their existing Open WebUI, pick the Learning Companion model, and ask a question.
- See the answer appear in Open WebUI, either all at once or word by word.
- Keep their personal API key in a private file that never gets shared or committed.
- Get a clear "your key is missing" message instead of a crash if the key is not set yet.

## Prerequisites

- Open WebUI is already installed and working for each participant. Do not install, rebuild, reconfigure, or modify it.
- Python 3.12 and `uv` are available on the machine.
- The instructor supplies the Grok model name. Each participant has their own Grok (xAI) API key.
- The repository currently holds only an empty `.gitignore` and an empty `docs/` folder. Keep the existing `.gitignore` and add to it; do not delete anything.

## Work to do

### Phase A — Architecture (do this first, then stop)

Create `docs/architecture.md`. Keep it to about one page, in plain English. It must record:

1. **The single classroom flow:**
   Open WebUI → this local application's OpenAI-compatible chat endpoint → LangChain prompt and Grok model → answer in Open WebUI.
2. **Open WebUI's role:** already installed and working for participants; it is the supplied chat client only. Participants must not reinstall, reconfigure, modify, or build Open WebUI.
3. **What we are building:** a small Learning Companion Chatbot. Not a custom frontend, and not a second demonstration app.
4. **The three endpoints:** `GET /health`, `GET /v1/models`, `POST /v1/chat/completions` (normal and streaming answers through the same chat route).
5. **Light boundaries:**
   - API keys live only in an untracked `.env` file.
   - Application instructions (the system prompt) are kept separate from user messages.
6. **Out of scope for this course:** authentication, authorization, security hardening, databases, persistent memory, RAG, production deployment, and extensive tests.
7. **Tech choices:** Python 3.12, `uv`, FastAPI, Pydantic settings, LangChain, `langchain-xai` (the Grok integration, class `ChatXAI`), Uvicorn, Ruff, pytest.

Then **stop** and ask the instructor:

> "I've written `docs/architecture.md`. Do you approve it so I can create the project seed?"

Before approval: do not create seed files, install dependencies, or scaffold code. If the instructor asks for changes, update `docs/architecture.md` and ask again. Resume this same story at Phase B only after an explicit "approved" (or equivalent).

### Phase B — Project seed (only after approval)

**Files to create or change**

| File | Action | What it holds |
|---|---|---|
| `pyproject.toml` | create | Project `learning-companion`, `requires-python = ">=3.12,<3.13"`, src layout, a `learning-companion` command that starts the server, Ruff settings |
| `uv.lock` | create (by `uv`) | Locked dependency versions |
| `.gitignore` | change | Add `.env`, `.venv/`, `__pycache__/`, `.ruff_cache/`, `.pytest_cache/` |
| `.env.example` | create | The canonical settings list (below) |
| `README.md` | create | Short setup and run steps, and the Open WebUI connection values |
| `src/learning_companion/__init__.py` | create | Empty package marker |
| `src/learning_companion/config.py` | create | Pydantic settings read from `.env` |
| `src/learning_companion/chain.py` | create | The one LangChain prompt → Grok → text flow |
| `src/learning_companion/main.py` | create | FastAPI app, the three routes, and `run()` to start Uvicorn |
| `tests/test_health.py` | create | One tiny check that `/health` answers. A placeholder so later stories have a test home |

**`.env.example`** — exactly these names, nothing else:

```
APP_ENV=development
GROK_API_KEY=
GROK_API_BASE_URL=https://api.x.ai/v1
GROK_MODEL_NAME=
HOST=127.0.0.1
PORT=8000
```

Note in the README: the instructor supplies `GROK_MODEL_NAME`; each participant copies `.env.example` to `.env` and puts their real key only in `.env`, which is never committed. Do not add Claude, other providers, database, or production settings.

**Settings (`config.py`)**

- One Pydantic `BaseSettings` class with the six fields above, reading `.env`.
- `GROK_API_KEY` and `GROK_MODEL_NAME` default to empty, so the app starts without them.

**The LangChain flow (`chain.py`)**

- A fixed Learning Companion instruction, for example: "You are a friendly Learning Companion. Explain ideas simply, check understanding, and encourage the learner."
- `ChatPromptTemplate` with that instruction as the system message and the latest user message as the human message.
- Piped into `ChatXAI(model=GROK_MODEL_NAME, api_key=GROK_API_KEY, xai_api_base=GROK_API_BASE_URL)`, then `StrOutputParser()`.
- Build the chain only when a request arrives (not at import time), so a missing key never stops the app from starting.
- No conversation history. Only the latest user message is used. That is Story 2.1.

**Routes (`main.py`)**

- `GET /health` → `{"status": "ok"}`.
- `GET /v1/models` → OpenAI-style list with one entry whose `id` is `GROK_MODEL_NAME`:
  `{"object": "list", "data": [{"id": "<model name>", "object": "model", "created": 0, "owned_by": "xai"}]}`.
  If the model name is blank, return an empty `data` list.
- `POST /v1/chat/completions`:
  - Request accepts `model`, `messages` (each with `role` of `system`, `user`, or `assistant`, and text `content`), and `stream` (default `false`). Ignore any other fields Open WebUI sends.
  - Before calling the model: if `GROK_API_KEY` or `GROK_MODEL_NAME` is blank, return an honest configuration error (HTTP 503) in OpenAI error shape, e.g. `{"error": {"message": "GROK_API_KEY is not set. Add it to your .env file and restart the app.", "type": "configuration_error"}}`.
  - `stream: false` → normal `chat.completion` JSON: `id`, `object`, `created`, `model`, and one choice with `message: {role: "assistant", content}` and `finish_reason: "stop"`.
  - `stream: true` → `text/event-stream` of `chat.completion.chunk` events, one per text piece (`delta: {content}`), then one chunk with an empty `delta` and `finish_reason: "stop"`, then `data: [DONE]`.
  - Both modes use the same chain (`invoke` for normal, `astream` for streaming).
- Do not add custom Open WebUI events, a second chat route, or a browser UI.

**Commands to run**

```bash
uv add fastapi "uvicorn[standard]" pydantic-settings langchain langchain-xai
uv add --dev ruff pytest httpx
cp .env.example .env          # then fill GROK_API_KEY and GROK_MODEL_NAME
uv run ruff format src tests
uv run ruff check --fix src tests
uv run learning-companion     # starts on http://127.0.0.1:8000
```

In a second terminal:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models
```

**Open WebUI connection values (document in README only; do not change Open WebUI itself)**

- Base URL: `http://127.0.0.1:8000/v1` (if the participant's Open WebUI runs in Docker, use `http://host.docker.internal:8000/v1`).
- API key field: any placeholder text; the real key stays in our `.env`.
- Model to select: the value of `GROK_MODEL_NAME`.

## Completion checks

Run only these lightweight checks:

1. `ruff format` and `ruff check` finish with no errors.
2. The app starts with `uv run learning-companion`, even with a blank key.
3. `/health` returns `{"status": "ok"}`.
4. `/v1/models` lists the configured Grok model.
5. In Open WebUI, with the model selected and streaming turned off, one question gets one Grok reply.
6. In Open WebUI, with streaming on (the default), one question gets a reply that appears word by word and finishes cleanly.
7. With a blank key, a chat attempt shows the clear configuration error, and the app keeps running.

**Expected classroom result:** one Grok reply from the Learning Companion is visible in Open WebUI.

Do not add a broad test suite, tool calls, LangGraph, agents, MCP, or advanced streaming features.

## Handover

- **Created or changed:** `docs/architecture.md`, `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example`, `README.md`, `src/learning_companion/` (`__init__.py`, `config.py`, `chain.py`, `main.py`), `tests/test_health.py`.
- **Not created:** `.env` contents are personal and never committed.
- **Story 2.1 will extend:** the prompt in `chain.py` into full prompt construction, and pass the conversation history from Open WebUI's `messages` list instead of only the latest user message. Routes, settings, and the Open WebUI connection stay the same.
