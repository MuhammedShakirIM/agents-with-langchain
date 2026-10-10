# Story 3.1 — Study-Helper Chain

Status: Ready for implementation
Course: Beginner LangChain and LangGraph classroom course
Capstone: Learning Companion Chatbot
Project path: repository root (no `docs/config.yaml` exists)
Builds on: Story 1.1 (architecture and project seed), Story 2.1 (LangChain prompt template), Story 2.2 (conversation history from the request)

---

## Purpose

Give the same Learning Companion Chatbot a second, focused way of answering: a **study helper** that explains a beginner technical idea in plain words and ends with one small next learning step. This story builds the study-helper chain and a small way to try it locally. It does **not** connect it to Open WebUI yet. Everything a participant sees in Open WebUI stays exactly as it is after Story 2.2. Story 3.2 adds the visible `/study` rule that picks between the two chains.

## What this story implements in plain English

- Chatting in Open WebUI works exactly as before: greetings and ordinary questions still get the friendly general Learning Companion reply, with follow-ups understood.
- The app now also has a study helper that can explain a technical idea such as "What is an API?" in plain language, with a small example when it helps.
- Every study-helper answer ends with one small, concrete suggestion for what to learn or try next.
- While developing, the implementer can ask the study helper a question from the terminal with one command and read its answer. Participants cannot reach it from Open WebUI until Story 3.2.
- Both ways of answering use the same Grok model, the same API key, and the same recent chat history; the app still saves nothing.

## Prerequisites

- Story 2.2 is complete: `chain.py` has `LEARNING_COMPANION_INSTRUCTION`, `MAX_HISTORY_MESSAGES`, `build_prompt()`, `latest_user_message()`, `history_messages()`, `chain_input()`, `describe_messages()`, and `build_chain()`; `main.py` uses `chain_input()` for both normal and streaming replies, and `ChatMessage` accepts `role: str` and `content: str | list | None`.
- `uv run learning-companion` starts the app, and a two-turn chat in Open WebUI gets history-aware Grok replies, normal and streaming.
- `.env` holds a working `GROK_API_KEY` and `GROK_MODEL_NAME`. Open WebUI is connected to `http://127.0.0.1:8000/v1` (or `http://host.docker.internal:8000/v1`). Do not change Open WebUI.
- No new dependencies. Everything needed is already in `langchain-core` and `langchain-xai`. Do not run `uv add`.

## Work to do

### Files to change

| File | Action | What changes |
|---|---|---|
| `src/learning_companion/chain.py` | change (add only) | Add the study-helper instruction, its prompt, and its chain next to the existing general-chat ones |
| `src/learning_companion/try_study_helper.py` | create | A tiny development script that sends one question to the study-helper chain and prints the answer |
| `docs/architecture.md` | change | Add the two chain behaviours and their responsibilities |

Do not change `main.py`, `config.py`, `.env.example`, `pyproject.toml`, `uv.lock`, `README.md`, `tests/test_health.py`, the routes, the request/response shapes, or the Open WebUI connection.

### 1. Leave the general-chat chain untouched (`chain.py`)

- `LEARNING_COMPANION_INSTRUCTION`, `build_prompt()`, and `build_chain()` stay exactly as Story 2.2 left them. This is the **general-chat chain**, and it keeps handling every Open WebUI message.
- Do not rename, merge, or "share" parts of it with the new chain. Copying the four-line `ChatXAI(...)` setup into the new chain is fine and keeps both easy to read.
- `MAX_HISTORY_MESSAGES`, `latest_user_message()`, `history_messages()`, `chain_input()`, and `describe_messages()` are reused as-is.

### 2. Study-helper instruction (`chain.py`)

Add one stable, application-owned constant below the existing instruction:

```python
STUDY_HELPER_INSTRUCTION = (
    "You are the Learning Companion's study helper for beginners. "
    "Explain the technical idea the learner asks about in plain, everyday language. "
    "Keep it short: a brief explanation, then one small example only if it helps. "
    "Avoid jargon; if you must use a technical word, explain it in plain words first. "
    "End with exactly one line that starts with 'Next step:' and suggests one small, "
    "concrete thing the learner can try or read about next. "
    "Do not claim to have researched, browsed the web, or looked up course material, "
    "and do not promise the answer is guaranteed correct. If you are unsure, say so."
)
```

- It is a fixed `SystemMessage`, never filled in from a request. The learner's text only ever goes into the human message and history.

### 3. Study-helper prompt and chain (`chain.py`)

Add two functions after `build_chain()`, built the same way as the general-chat ones:

```python
def build_study_helper_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=STUDY_HELPER_INSTRUCTION),
            MessagesPlaceholder("history", optional=True),
            HumanMessagePromptTemplate.from_template("{user_message}"),
        ]
    )


def build_study_helper_chain():
    """Study-helper prompt → Grok → text. Built per request so a missing key never blocks startup."""
    model = ChatXAI(
        model=settings.grok_model_name,
        api_key=settings.grok_api_key,
        xai_api_base=settings.grok_api_base_url,
    )
    return build_study_helper_prompt() | model | StrOutputParser()
```

- Same input as the general-chat chain: `chain_input(messages)` → `{"history": [...], "user_message": "..."}`. Same Grok settings, same history limit, same output (plain text, so `ainvoke` and `astream` both work later).
- No routing, classification, tool calls, loops, review steps, LangGraph, or agent logic.

### 4. Local development script (`try_study_helper.py`)

Create `src/learning_companion/try_study_helper.py`, run as a module:

```bash
uv run python -m learning_companion.try_study_helper "What is an API?"
```

It should:

- Read the question from the command-line arguments (join them into one string). If none is given, print a one-line usage hint and exit.
- If `settings.grok_api_key` or `settings.grok_model_name` is blank, print the same plain message the app uses (for example "GROK_API_KEY is not set. Add it to your .env file and restart the app.") and exit with status 1.
- Build the input the same way the app does: `chain_input([ChatMessage(role="user", content=question)])`, importing `ChatMessage` from `learning_companion.main`.
- Call `build_study_helper_chain().invoke(inputs)` and print the answer.

Keep it about 20 lines. No arguments parser library, no history file, no interactive loop, no new `[project.scripts]` entry.

### 5. Update `docs/architecture.md`

Add a short "Chain behaviours" section after "Message flow":

| Chain | Built by | Responsibility | Reached from Open WebUI? |
|---|---|---|---|
| General chat | `build_chain()` | Friendly Learning Companion replies for greetings and ordinary conversation | Yes — every chat message (unchanged) |
| Study helper | `build_study_helper_chain()` | Plain-language explanation of a beginner technical idea, a small example where useful, and one "Next step:" line | Not yet — only through `try_study_helper.py` during development |

Add these lines under the table:

- Both chains use the same Grok model and settings, the same `chain_input()` (recent history + latest question), and the same OpenAI-compatible chat endpoint and Open WebUI conversation.
- Each chain has its own fixed instruction, kept separate from user content.
- This story only adds the study-helper capability. Choosing between the two chains is the next story (3.2, the `/study` rule). Neither chain is an autonomous agent: there are no tools, loops, or self-directed decisions.

### Commands to run

```bash
uv run ruff format src tests
uv run ruff check --fix src tests
uv run learning-companion     # starts on http://127.0.0.1:8000
```

In a second terminal:

```bash
uv run python -m learning_companion.try_study_helper "What is an API?"
```

Then send one ordinary message in Open WebUI (see Completion checks). Record in the Handover the commands actually run and their results.

### Not in this story

Routing or the `/study` rule, LLM-based classification, more specialist chains, a new endpoint, a second app, a new UI, another model provider, a database, retrieval/RAG, MCP, tool calls, LangGraph, autonomous agents, loops, review steps, a broad test suite, production controls.

## Completion checks

1. `ruff format` and `ruff check` finish with no errors.
2. **General chat unchanged:** with the app running, in a new Open WebUI chat with the Learning Companion model selected, send *"Hi! Can you help me learn today?"*
   **Expected:** a friendly general Learning Companion reply that streams word by word and finishes cleanly, just like after Story 2.2. It does not end with a "Next step:" line. The terminal shows the same one-line message description as before.
3. **Study helper works locally:** `uv run python -m learning_companion.try_study_helper "What is an API?"`
   **Expected:** a short, plain-language explanation of an API (a small example is fine), ending with exactly one line that starts with `Next step:`. No claims of research, browsing, or looked-up course material.

## Handover

- **Changed:** `src/learning_companion/chain.py` (additions only), `docs/architecture.md`.
- **Created:** `src/learning_companion/try_study_helper.py`.
- **Unchanged:** `main.py`, the general-chat chain, routes, request/response shapes, normal and streaming behaviour, Grok settings, `.env.example`, dependencies, conversation-history handling, and the Open WebUI connection.
- **Commands actually run:** _implementer fills in (expected: the four commands above, plus the one Open WebUI message)._
- **Observed results:** _implementer fills in (the Open WebUI general reply, and the study-helper answer with its `Next step:` line)._
- **Story 3.2 will extend:** `main.py`'s chat route with one visible rule: a latest user message starting with `/study` goes to `build_study_helper_chain()` (with the prefix removed), everything else goes to the unchanged `build_chain()`. Same endpoint, same `chain_input()`, same normal and streaming responses, and the development log names which chain was used. `try_study_helper.py` stays as a development helper.
