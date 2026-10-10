# Story 2.1 — LangChain Prompt Template

Status: Ready for implementation
Course: Beginner LangChain and LangGraph classroom course
Capstone: Learning Companion Chatbot
Project path: repository root (no `docs/config.yaml` exists)
Builds on: Story 1.1 (architecture and project seed)

---

## Purpose

Make the seed's LangChain flow reusable and easy to understand. The prompt becomes a small, clearly built chat prompt with two separate parts: the application's fixed Learning Companion instruction, and the participant's current message. Everything else stays the same: the three endpoints, normal and streaming answers, the Grok settings, and the Open WebUI connection.

## What this story implements in plain English

For a participant using the chatbot in Open WebUI:

- Chatting looks and works exactly as before: ask a question, get a Learning Companion answer, all at once or word by word.
- The Learning Companion's personality always comes from the app. A participant's own "system prompt" text in Open WebUI cannot replace it.
- The chatbot still answers only the latest question. It does not remember earlier turns yet.
- While the app runs on a laptop, its terminal shows a short line describing what was sent to Grok (which kinds of messages, how many, in what order). It never shows the API key or the full hidden instruction.

## Prerequisites

- Story 1.1 is complete: `uv run learning-companion` starts the app, and one question in Open WebUI gets a Grok reply in both normal and streaming mode.
- `.env` holds a working `GROK_API_KEY` and `GROK_MODEL_NAME`.
- Open WebUI is already connected to `http://127.0.0.1:8000/v1` (or `http://host.docker.internal:8000/v1`). Do not change Open WebUI.
- No new dependencies. Everything needed is in `langchain-core` (already installed through `langchain` and `langchain-xai`). Do not run `uv add`.

## Work to do

### Files to change

| File | Action | What changes |
|---|---|---|
| `src/learning_companion/chain.py` | change | Build the two-part prompt, pick the latest user message, keep the one prompt → Grok → text chain, add the small message-description helper |
| `src/learning_companion/main.py` | change | Use the helpers from `chain.py` for both normal and streaming paths; log the message description in development |
| `docs/architecture.md` | change | Add the message flow and the no-persistence boundary |

Do not change `config.py`, `.env.example`, `pyproject.toml`, `uv.lock`, `README.md`, the routes, the request/response shapes, or `tests/test_health.py`.

### 1. Two-part prompt (`chain.py`)

- Keep `LEARNING_COMPANION_INSTRUCTION` as the one stable, application-owned instruction.
- Replace the seed's `("system", ...)` / `("human", "{question}")` tuples with LangChain message abstractions:
  - `SystemMessage(content=LEARNING_COMPANION_INSTRUCTION)` — a fixed message, not a template, so braces or text in it are never filled in from a request.
  - `HumanMessagePromptTemplate.from_template("{user_message}")` — the participant's current message.
  - Combine them with `ChatPromptTemplate.from_messages([...])` in a `build_prompt()` function.
- Do not build a long string by joining the instruction and the user text together.

### 2. Pick the latest user message (`chain.py`)

- Add `latest_user_message(messages) -> str`: walk the OpenAI-style `messages` list from the end and return the content of the last message whose `role` is `user`.
- Messages with `role: "system"` from the request are participant-provided content (for example, an Open WebUI custom system prompt). They must never take the place of `LEARNING_COMPANION_INSTRUCTION`. In this story they are not forwarded to Grok; they are only counted in the development log.
- Ignore `assistant` messages. No history handling; Story 2.2 adds it.
- If no user message exists, use an empty string (same as the seed).

### 3. One chain for both paths (`chain.py`, `main.py`)

- `build_chain()` stays as `build_prompt() | ChatXAI(...) | StrOutputParser()`, built per request so a missing key never blocks startup.
- Add `chain_input(messages) -> dict` returning `{"user_message": latest_user_message(messages)}`.
- In `main.py`, compute `inputs = chain_input(request.messages)` once and pass it to `chain.ainvoke(inputs)` for normal answers and `chain.astream(inputs)` for streaming. No second chat path, no custom message format, no Open WebUI plugins or events.
- Keep the configuration-error check, the `chat.completion` JSON, and the `chat.completion.chunk` SSE stream exactly as they are.

### 4. Development-only message description (`chain.py`, `main.py`)

- Add `describe_messages(request_messages, prompt_messages) -> str` that returns one compact line, for example:
  `request: system=1 user=3 assistant=2 | to model: [system, human] (user_message 42 chars)`
- It shows roles, counts, order, and the user message length only. Never the API key, never the instruction text, never the full user text.
- In `main.py`, when `settings.app_env == "development"`, render the prompt with `build_prompt().format_messages(**inputs)` and log the description with Python's `logging` (one `logger.info` line per chat request). No log in other environments.

### 5. Update `docs/architecture.md`

Add a short "Message flow" section and one boundary line:

```
Open WebUI messages list
  → pick the latest user message (request system messages never replace ours)
  → LangChain prompt: [fixed Learning Companion instruction (system), latest user message (human)]
  → Grok (ChatXAI) → text
  → same OpenAI-style JSON or SSE stream back to Open WebUI
```

- **No persistence:** the app keeps nothing between requests. No database, no saved conversations, no memory. Each request carries everything it needs.

### Commands to run

```bash
uv run ruff format src tests
uv run ruff check --fix src tests
uv run learning-companion     # starts on http://127.0.0.1:8000
```

Then ask one ordinary question in Open WebUI (see Completion checks). Record in the Handover the commands actually run and their results.

### Not in this story

Command-line chatbot, second chat route, conversation history, database, persistent memory, RAG, tools, MCP, LangGraph, new frontend, evaluation harness, broad test suite, security programme.

## Completion checks

1. `ruff format` and `ruff check` finish with no errors.
2. The app starts with `uv run learning-companion`; `/health` and `/v1/models` answer as before.
3. In Open WebUI, with the Learning Companion model selected, ask one ordinary question, for example: *"What is a variable in Python?"*
4. **Expected Open WebUI result:** a friendly Learning Companion answer appears word by word and finishes cleanly, just like after Story 1.1.
5. The app terminal shows one line like `request: ... | to model: [system, human] (user_message N chars)` — system first, latest user message second — with no key or instruction text visible.

## Handover

- **Changed:** `src/learning_companion/chain.py`, `src/learning_companion/main.py`, `docs/architecture.md`.
- **Unchanged:** routes, request/response shapes, normal and streaming behaviour, settings, `.env.example`, dependencies, and the Open WebUI connection.
- **Commands actually run:** _implementer fills in (expected: the three commands above, plus the one Open WebUI question)._
- **Observed Open WebUI result:** _implementer fills in._
- **Story 2.2 will extend:** `chain_input` and `build_prompt` to carry the conversation history from Open WebUI's `messages` list (adding a LangChain messages placeholder between the fixed instruction and the latest user message), decide how request `system` messages appear as user-side content, and keep the same no-persistence boundary: history comes from each request, never from storage.
