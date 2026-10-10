# Story 2.2 — Conversation History from the Request

Status: Ready for implementation
Course: Beginner LangChain and LangGraph classroom course
Capstone: Learning Companion Chatbot
Project path: repository root (no `docs/config.yaml` exists)
Builds on: Story 1.1 (architecture and project seed), Story 2.1 (LangChain prompt template)

---

## Purpose

Let the Learning Companion answer follow-up questions. Open WebUI already sends the earlier messages of the active chat with every request. This story passes a short, recent slice of those messages to Grok through the existing prompt template, so "show me an example of that" makes sense. Nothing is saved: each request carries its own history, and the app forgets it when the reply is done.

## What this story implements in plain English

- When a participant asks a follow-up, Open WebUI sends the whole visible chat along with it; the app now passes the recent part of that chat to Grok, not just the last question.
- Earlier questions and earlier answers go to Grok in the same order they appeared in the chat, followed by the new question.
- Only the last 10 earlier messages are used, so a long chat stays small and fast.
- The Learning Companion's own instruction always comes first; a participant's "system prompt" text in Open WebUI cannot replace it, and odd messages (images, empty or unknown kinds) are skipped instead of breaking the chat.
- The app keeps nothing afterwards. A new Open WebUI chat starts fresh, and restarting the app loses nothing because nothing was stored.

## Prerequisites

- Story 2.1 is complete: `chain.py` has `LEARNING_COMPANION_INSTRUCTION`, `build_prompt()`, `latest_user_message()`, `chain_input()`, `describe_messages()`, and `build_chain()`; `main.py` uses `chain_input()` for both normal and streaming replies and logs one description line in development.
- `uv run learning-companion` starts the app and one question in Open WebUI gets a Grok reply, normal and streaming.
- `.env` holds a working `GROK_API_KEY` and `GROK_MODEL_NAME`. Open WebUI is connected to `http://127.0.0.1:8000/v1` (or `http://host.docker.internal:8000/v1`). Do not change Open WebUI.
- No new dependencies. `MessagesPlaceholder`, `HumanMessage`, and `AIMessage` are in `langchain-core`, already installed. Do not run `uv add`.

## Work to do

### Files to change

| File | Action | What changes |
|---|---|---|
| `src/learning_companion/chain.py` | change | Add the history limit, the history placeholder in the prompt, history conversion in `chain_input`, and history counts in `describe_messages` |
| `src/learning_companion/main.py` | change | Let the request model accept unusual roles and non-text content without rejecting the request, so they can be skipped safely |
| `docs/architecture.md` | change | Update the message flow with request-provided history, the message limit, and the no-persistence boundary |

Do not change `config.py`, `.env.example`, `pyproject.toml`, `uv.lock`, `README.md`, the routes, the response shapes, or `tests/test_health.py`.

### 1. History limit (`chain.py`)

- Add one constant next to the instruction: `MAX_HISTORY_MESSAGES = 10`.
- It counts earlier `user` and `assistant` messages only (not the latest question, not system messages). Keep it a code constant; do not add a new `.env` setting.

### 2. History placeholder in the prompt (`chain.py`)

`build_prompt()` becomes three parts, in this order:

```python
ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=LEARNING_COMPANION_INSTRUCTION),
        MessagesPlaceholder("history", optional=True),
        HumanMessagePromptTemplate.from_template("{user_message}"),
    ]
)
```

- The fixed instruction stays a `SystemMessage`, never filled from a request.
- History goes in through `MessagesPlaceholder`, never by joining text into one string.

### 3. Convert request messages into history (`chain.py`)

Add `history_messages(messages) -> list[BaseMessage]`:

- Find the position of the latest `user` message (the same one `latest_user_message` returns). Only messages **before** it are history.
- From those, keep only messages whose `role` is `user` or `assistant` **and** whose `content` is a non-empty string.
  - `user` → `HumanMessage(content=...)`, `assistant` → `AIMessage(content=...)`.
  - `system` messages from the request are skipped. They never replace or add to the application's instruction.
  - Unknown roles (for example `tool`) and non-text content (for example a list of image parts) are skipped silently.
- Keep the original order, then keep only the last `MAX_HISTORY_MESSAGES`.

Update `chain_input(messages)` to return:

```python
{"history": history_messages(messages), "user_message": latest_user_message(messages)}
```

`latest_user_message` must also skip a latest `user` message whose content is not a string, falling back to the previous text one (or `""`).

### 4. Same chain for both paths (`main.py`)

- Keep `inputs = chain_input(request.messages)` computed once, passed to `chain.ainvoke(inputs)` for normal replies and `chain.astream(inputs)` for streaming. Same `build_prompt() | ChatXAI(...) | StrOutputParser()` chain.
- Relax `ChatMessage` so unsupported entries are tolerated rather than rejected with a 422:
  - `role: str`
  - `content: str | list | None = None`
- Request fields (`model`, `messages`, `stream`), the configuration-error check, the `chat.completion` JSON, and the `chat.completion.chunk` SSE stream stay exactly as they are.

### 5. Compact development log (`chain.py`, `main.py`)

- Extend `describe_messages(request_messages, prompt_messages)` to show the role sequence sent to the model and the history count, for example:
  `request: system=1 user=2 assistant=1 | to model: [system, human, ai, human] (history 2/10, user_message 31 chars)`
- Roles, counts, order, and lengths only. Never the API key, the instruction text, or any message body.
- `main.py` keeps logging this one line per chat request, only when `settings.app_env == "development"`.

### 6. Update `docs/architecture.md`

Replace the "Message flow" section with:

```
Open WebUI messages list (the active chat, sent with every request)
  → latest user message = the new question
  → earlier user/assistant text messages = history (last 10, original order)
  → request system messages, unknown roles, non-text content: skipped
  → LangChain prompt: [fixed instruction (system), history placeholder, latest question (human)]
  → Grok (ChatXAI) → text
  → same OpenAI-style JSON or SSE stream back to Open WebUI
```

And keep the boundary line, now explicit about history:

- **No persistence:** history comes only from the current request. The app saves nothing after a reply: no database, no saved conversations, no memory across chats or restarts.

### Commands to run

```bash
uv run ruff format src tests
uv run ruff check --fix src tests
uv run learning-companion     # starts on http://127.0.0.1:8000
```

Then run the two-turn Open WebUI check below. Record in the Handover the commands actually run and their results.

### Not in this story

Database, persistent or cross-session memory, summarising old messages, RAG, tools, MCP, routing, LangGraph, a new endpoint, a new UI, an evaluation harness, a broad test suite.

## Completion checks

1. `ruff format` and `ruff check` finish with no errors.
2. The app starts with `uv run learning-companion`; `/health` and `/v1/models` answer as before.
3. In a **new** Open WebUI chat with the Learning Companion model selected, ask:
   - Turn 1: *"I'm learning about Python lists. Explain what a list is in two sentences."*
   - Turn 2: *"Now show me one short example of that."*
4. **Expected Open WebUI result:** turn 1 gets a short explanation of lists. Turn 2 gets a short Python example that uses a list, without asking "example of what?". Both replies stream word by word and finish cleanly.
5. The app terminal shows, for turn 2, a line like
   `request: user=2 assistant=1 | to model: [system, human, ai, human] (history 2/10, ...)`
   (a `system=1` count may also appear if Open WebUI sends its own system prompt; it must not appear in the model sequence beyond the first `system`). No key, instruction text, or message body is visible.
6. Optional quick check with streaming turned off in Open WebUI: the same two turns give the same kind of answers.

## Handover

- **Changed:** `src/learning_companion/chain.py`, `src/learning_companion/main.py`, `docs/architecture.md`.
- **Unchanged:** routes, response shapes, request fields, normal and streaming behaviour, Grok settings, `.env.example`, dependencies, and the Open WebUI connection.
- **Commands actually run:** _implementer fills in (expected: the three commands above, plus the two-turn Open WebUI chat)._
- **Observed Open WebUI result:** _implementer fills in (turn 2 reply and the logged role sequence)._
- **Story 3.1 will extend:** the history-aware prompt → Grok → text step built here. It reuses `chain_input()` (history + latest question) and `MAX_HISTORY_MESSAGES` as-is, keeps the same endpoints and Open WebUI connection, and keeps the no-persistence boundary: history still comes from each request, never from storage.
