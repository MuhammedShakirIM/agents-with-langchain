# Story 3.2 — Visible Python Routing (`/study`)

Status: Ready for implementation
Course: Beginner LangChain and LangGraph classroom course
Capstone: Learning Companion Chatbot
Project path: repository root (no `docs/config.yaml` exists)
Builds on: Story 1.1 (architecture and project seed), Story 2.1 (LangChain prompt template), Story 2.2 (conversation history from the request), Story 3.1 (study-helper chain)

---

## Purpose

Make both existing chains reachable from the participant's existing Open WebUI chat, through the same chat endpoint. One plain Python `if/else` picks the chain: a message that starts with `/study` goes to the study helper; everything else goes to the general-chat chain. The rule sits in plain sight so participants can read it, see which way each message went, and later watch Session 4 replace this same `if/else` with an explicit LangGraph route.

## What this story implements in plain English

- An ordinary message, such as "Hi! Can you help me learn today?", goes to the friendly general Learning Companion, exactly as before.
- A message that starts with `/study`, such as "/study Explain what an API is", goes to the study helper instead. The `/study` word is removed first, so the study helper only sees "Explain what an API is".
- The study helper answers with a plain-language explanation and ends with one "Next step:" line.
- Both kinds of message use the same Open WebUI chat, the same connection, and the same recent chat history; replies still appear all at once or word by word as before.
- While developing, each reply starts with a short label ("Route: general chat" or "Route: study helper"), and the app's terminal logs which route was picked, so the class can see the decision happen.

## Prerequisites

- Story 3.1 is complete: `chain.py` has `build_chain()` (general chat), `build_study_helper_prompt()`, `build_study_helper_chain()`, `build_prompt()`, `chain_input()`, `history_messages()`, `latest_user_message()`, and `describe_messages()`; `try_study_helper.py` answers "What is an API?" with a `Next step:` line.
- `main.py` uses `chain_input()` once per request, passes it to `ainvoke` (normal) and `astream` (streaming), and logs one message-description line when `settings.app_env == "development"`.
- `uv run learning-companion` starts the app and Open WebUI gets history-aware general-chat replies, normal and streaming.
- `.env` holds a working `GROK_API_KEY` and `GROK_MODEL_NAME`, with `APP_ENV=development`. Open WebUI is connected to `http://127.0.0.1:8000/v1` (or `http://host.docker.internal:8000/v1`). Do not change Open WebUI.
- No new dependencies. Do not run `uv add`.

## Work to do

### Files to change

| File | Action | What changes |
|---|---|---|
| `src/learning_companion/chain.py` | change (add only) | Add `STUDY_COMMAND` and one small `choose_route()` function |
| `src/learning_companion/main.py` | change | Use `choose_route()` in the chat route to pick the chain, log the route, and add the development route label to the answer |
| `docs/architecture.md` | change | Add the `/study` rule, the selected-chain path, and the routing boundary |

Do not change `config.py`, `.env.example`, `pyproject.toml`, `uv.lock`, `README.md`, `try_study_helper.py`, `tests/test_health.py`, the two chains, the routes, the request fields, or the Open WebUI connection.

### 1. The visible rule (`chain.py`)

Add next to the instructions:

```python
STUDY_COMMAND = "/study"


def choose_route(user_message: str) -> tuple[str, str]:
    """The one routing rule: '/study ...' goes to the study helper, everything else to general chat."""
    parts = user_message.strip().split(maxsplit=1)
    if parts and parts[0] == STUDY_COMMAND:
        return "study", parts[1] if len(parts) > 1 else ""
    return "general", user_message
```

- Only the latest user message is checked. The match is exact and case-sensitive on the first word, so "/studying" or "Let's /study" stay on general chat.
- Only the leading `/study` word is removed. Nothing else in the question changes.
- `/study` with nothing after it still goes to the study helper with an empty question; the study helper will simply ask what to explain. No extra handling.
- No LLM call, keyword list, scoring, or classification.

### 2. Pick the chain in the chat route (`main.py`)

Right after `inputs = chain_input(request.messages)`:

```python
route, inputs["user_message"] = choose_route(inputs["user_message"])
if route == "study":
    chain = build_study_helper_chain()
    prompt = build_study_helper_prompt()
else:
    chain = build_chain()
    prompt = build_prompt()
```

- History is untouched: `inputs["history"]` stays exactly as Story 2.2 builds it from the other request messages (last 10 user/assistant text messages, system and odd messages skipped). Earlier `/study` messages in the history keep their wording as typed.
- The chosen `chain` then goes through the existing adapter unchanged: `chain.ainvoke(inputs)` for normal replies and `chain.astream(inputs)` for streaming.
- The configuration-error check, the `chat.completion` JSON, the `chat.completion.chunk` SSE stream, and `data: [DONE]` stay exactly as they are. No new fields, no custom events, no second endpoint.

### 3. Development-only route log and label (`main.py`)

Only when `settings.app_env == "development"`:

- **Log:** put the route at the front of the existing one-line description, built from the selected `prompt`:
  `route=study | request: user=1 | to model: [system, human] (history 0/10, user_message 22 chars)`
  Route name, roles, counts, and lengths only. Never the key, instruction text, or message bodies.
- **Label in the answer text:** start the reply with one short line, then a blank line:
  - general: `Route: general chat`
  - study: `Route: study helper`
  - Normal replies: prepend it to `content`. Streaming replies: send it as the first `delta.content` chunk before the chain's pieces. The response shape stays standard OpenAI-compatible; the label is just text.

Outside development there is no log line and no label. Do not add custom response fields or Open WebUI plugins.

### 4. Update `docs/architecture.md`

Add a short "Routing" section after "Chain behaviours":

```
Latest user message
  → starts with "/study"?  yes → remove "/study" → study-helper chain
                           no  → general-chat chain (unchanged)
  → same chain_input history, same Grok settings
  → same OpenAI-style JSON or SSE stream back to Open WebUI
```

- The rule is one `if/else` in plain Python (`choose_route()` in `chain.py`, used in `main.py`'s chat route).
- In development, the terminal log and a one-line "Route: …" label at the top of the reply show which chain answered.
- **Boundary:** this is deterministic application routing. It is not LLM classification, not LangGraph, and not multi-agent orchestration. Session 4 will replace this `if/else` internally with an explicit LangGraph route; the endpoint and Open WebUI experience stay the same.

In the "Chain behaviours" table, change the study helper's "Reached from Open WebUI?" cell to: "Yes — messages starting with `/study`". Change the general chat cell to: "Yes — every other message".

### Commands to run

```bash
uv run ruff format src tests
uv run ruff check --fix src tests
uv run learning-companion     # starts on http://127.0.0.1:8000
```

Then send the two Open WebUI messages below. Record in the Handover the commands actually run and their results.

### Not in this story

LLM-based routing or classification, more specialist chains, review steps, loops, LangGraph, agents, tools, MCP, a new endpoint, custom response fields, Open WebUI plugins or settings changes, a database, a broad test suite, production controls.

## Completion checks

1. `ruff format` and `ruff check` finish with no errors.
2. **General route:** in a new Open WebUI chat with the Learning Companion model selected, send *"Hi! Can you help me learn today?"*
   **Expected Open WebUI result:** the reply starts with `Route: general chat`, then a friendly Learning Companion answer that streams word by word and finishes cleanly. It does not end with a `Next step:` line.
3. **Study route:** in the same chat, send *"/study Explain what an API is"*
   **Expected Open WebUI result:** the reply starts with `Route: study helper`, then a short, plain-language explanation of an API (a small example is fine), ending with exactly one line that starts with `Next step:`. It streams and finishes cleanly.
4. **Route log:** the app terminal shows one line per message, `route=general | …` for the first and `route=study | …` for the second, with no key, instruction text, or message body.
5. Both replies came through the same `POST /v1/chat/completions` endpoint in the same Open WebUI chat; nothing in Open WebUI was changed.

## Handover

- **Changed:** `src/learning_companion/chain.py` (additions only), `src/learning_companion/main.py`, `docs/architecture.md`.
- **Unchanged:** both chains and their instructions, `try_study_helper.py`, routes, request fields, response shapes, normal and streaming behaviour, Grok settings, `.env.example`, dependencies, conversation-history handling, and the Open WebUI connection.
- **Commands actually run:** _implementer fills in (expected: the three commands above, plus the two Open WebUI messages)._
- **Observed Open WebUI results:** _implementer fills in (the general reply with its label, the study reply with its label and `Next step:` line, and the two route log lines)._
- **Story 4.1 will extend:** the `if/else` in `main.py`'s chat route. It will be replaced internally by an explicit LangGraph graph: a route step that reuses `choose_route()`, one node for the general-chat chain, and one node for the study-helper chain. The same `/study` rule, `chain_input()` history, endpoint, normal and streaming adapter, development route log and label, and Open WebUI experience stay the same; only how the choice is wired inside the app changes.
