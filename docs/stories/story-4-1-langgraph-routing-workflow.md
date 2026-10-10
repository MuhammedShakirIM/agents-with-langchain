# Story 4.1 — LangGraph Routing Workflow

Status: Ready for implementation
Course: Beginner LangChain and LangGraph classroom course
Capstone: Learning Companion Chatbot
Project path: repository root (no `docs/config.yaml` exists)
Builds on: Story 1.1 (architecture and project seed), Story 2.1 (LangChain prompt template), Story 2.2 (conversation history from the request), Story 3.1 (study-helper chain), Story 3.2 (visible Python routing)

---

## Purpose

Replace the small `if/else` inside the chat route (Story 3.2) with one small LangGraph workflow that does the same job in a form participants can see: a router step, two answer steps, and the arrows between them. The `/study` rule, both LangChain chains, the chat endpoint, the history handling, the Grok settings, and everything a participant sees in Open WebUI stay the same. Only how the choice is wired inside the app changes.

## What this story implements in plain English

- A question typed in Open WebUI arrives at the same chat endpoint as before, with the same recent chat history.
- A router step looks at the latest message. If it starts with `/study`, it marks the question "study" and removes the `/study` word; otherwise it marks it "general". This is the same plain rule as Story 3.2, with no AI involved.
- Based on that mark, the question goes to exactly one answer step: the general Learning Companion, or the study helper. Each one asks Grok through its existing LangChain chain and writes down the finished answer.
- The finished answer goes back to Open WebUI exactly as before, all at once or word by word, with the same development "Route: …" label at the top.
- In development, the app's terminal prints one short line showing which way the question went and which steps ran, for example `START → router → study_helper → END`.

### What the workflow keeps track of while answering one question (the state)

The workflow carries one small record from step to step. It lives only for one question and is never saved.

| Field | Plain meaning | Who fills it in |
|---|---|---|
| `user_message` | The latest thing the participant typed (with `/study` removed once routed) | The chat route, then the router |
| `messages` | The recent earlier chat messages Open WebUI sent with the question (the history, up to 10) | The chat route |
| `route` | Which way the question goes: `general` or `study` | The router |
| `final_answer` | The finished reply text | The answer step that ran |

### Words used in this story

- **Graph (workflow):** the whole map of steps and arrows. One question walks through it once from `START` to `END`.
- **Node (step):** one focused piece of work. A node is **not automatically an agent**.
- **Router node:** ordinary application logic, a plain Python `if`. It makes no AI call and no free choice.
- **General-chat node and study-helper node:** the two Grok-powered answer steps. They can be called small specialist behaviours: each one does one job with one fixed instruction. They use no tools and make no plans.
- **Edge (arrow):** says which step runs next. A **conditional edge** picks the next step by reading `route`.
- **MCP:** a future node could call an outside tool through MCP. That is explicitly **not** part of this course story.

## Prerequisites

- Story 3.2 is complete: `chain.py` has `build_chain()`, `build_prompt()`, `build_study_helper_chain()`, `build_study_helper_prompt()`, `chain_input()`, `describe_messages()`, `STUDY_COMMAND`, and `choose_route()`; `main.py`'s chat route uses `choose_route()` in an `if/else` to pick the chain, logs `route=… | …`, and adds the `Route: …` label in development.
- `uv run learning-companion` starts the app, and in Open WebUI both an ordinary message and a `/study` message get the right labelled reply, normal and streaming.
- `.env` holds a working `GROK_API_KEY` and `GROK_MODEL_NAME`, with `APP_ENV=development`. Open WebUI is connected to `http://127.0.0.1:8000/v1` (or `http://host.docker.internal:8000/v1`). Do not change Open WebUI.
- One new dependency is needed: `langgraph`. It is added once with `uv add langgraph` (see Commands).

## Work to do

### Files to change

| File | Action | What changes |
|---|---|---|
| `src/learning_companion/graph.py` | create | The graph state, the three nodes, the edges, and the compiled graph |
| `src/learning_companion/main.py` | change | The chat route runs the graph instead of the `if/else`; the development log shows the node sequence |
| `pyproject.toml`, `uv.lock` | change (by `uv add` only) | Add `langgraph` |
| `docs/architecture.md` | change | Add the graph diagram, state fields, node responsibilities, edge rules, and what stays out of scope |

Do not change `chain.py`, `config.py`, `.env.example`, `README.md`, `try_study_helper.py`, `tests/test_health.py`, the two chains or their instructions, `choose_route()`, the endpoints, the request fields, the response shapes, or the Open WebUI connection. Do not create a second app or a second chat route.

### 1. The graph (`graph.py`)

Keep the whole file short and readable top to bottom: state, nodes, edges.

```python
from typing import Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph

from learning_companion.chain import build_chain, build_study_helper_chain, choose_route


class LearningState(TypedDict):
    user_message: str
    messages: list[BaseMessage]
    route: Literal["general", "study"]
    final_answer: str


def router(state: LearningState) -> dict:
    """Ordinary Python, not an agent: the same /study rule as Story 3.2."""
    route, user_message = choose_route(state["user_message"])
    return {"route": route, "user_message": user_message}


async def general_chat(state: LearningState) -> dict:
    """Calls the existing general-chat chain and writes the final answer."""
    answer = await build_chain().ainvoke(
        {"history": state["messages"], "user_message": state["user_message"]}
    )
    return {"final_answer": answer}


async def study_helper(state: LearningState) -> dict:
    """Calls the existing study-helper chain and writes the final answer."""
    answer = await build_study_helper_chain().ainvoke(
        {"history": state["messages"], "user_message": state["user_message"]}
    )
    return {"final_answer": answer}


def next_node(state: LearningState) -> str:
    return state["route"]


def build_graph():
    graph = StateGraph(LearningState)
    graph.add_node("router", router)
    graph.add_node("general_chat", general_chat)
    graph.add_node("study_helper", study_helper)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", next_node, {"general": "general_chat", "study": "study_helper"})
    graph.add_edge("general_chat", END)
    graph.add_edge("study_helper", END)
    return graph.compile()


learning_graph = build_graph()
```

- Exactly three nodes and four edge rules. No reviewer, improver, loop, retry, tool, memory saver (checkpointer), or interrupt.
- The chains are still built inside the nodes per request, so a missing key never blocks startup. The configuration-error check in `main.py` still runs before the graph.
- The `/study` rule lives only in `choose_route()`. The router calls it; nothing else re-implements it.

### 2. Run the graph from the chat route (`main.py`)

Replace the Story 3.2 `if/else` that picks `chain` with:

```python
inputs = chain_input(request.messages)
state = {"user_message": inputs["user_message"], "messages": inputs["history"]}
```

The development "describe" prompt is still picked by route (`build_study_helper_prompt()` for `study`, `build_prompt()` for `general`) once the route is known.

**Normal reply:** run the graph and record which nodes ran:

```python
nodes, final = [], {}
async for update in learning_graph.astream(state, stream_mode="updates"):
    for node, values in update.items():
        nodes.append(node)
        final.update(values)
answer = final["final_answer"]
```

`final["route"]` gives the route for the label and log. `answer` goes into the same `chat.completion` JSON as before.

**Streaming reply:** run the graph once with two stream modes, `stream_mode=["updates", "messages"]`:

- An `"updates"` item from `router` gives the route: record the node and, in development, send the `Route: …` label as the first `delta.content` chunk.
- An `"updates"` item from an answer node: record the node name.
- A `"messages"` item is `(token_chunk, metadata)`. When `metadata["langgraph_node"]` is `general_chat` or `study_helper` and the chunk has text, send it as a `delta.content` chunk, exactly like the chain pieces were sent before.
- Then the same final `finish_reason: "stop"` chunk and `data: [DONE]`.

The `chat.completion` JSON, the `chat.completion.chunk` SSE stream, and `data: [DONE]` stay exactly as they are. No new response fields, no custom events, no graph data sent to Open WebUI.

### 3. Compact development trace (`main.py`)

Only when `settings.app_env == "development"`, after the reply finishes, log one line that adds the node sequence to the Story 3.2 line:

```
route=study | graph: START → router → study_helper → END | request: user=1 | to model: [system, human] (history 0/10, user_message 22 chars)
```

Route name, node names, roles, counts, and lengths only. Never the API key, the instruction text, or message bodies. The `Route: general chat` / `Route: study helper` label at the top of the reply stays as in Story 3.2. Outside development: no trace line and no label. No tracing platform (such as LangSmith) and no graph image export.

### 4. Update `docs/architecture.md`

Replace the "Routing" section with a short "LangGraph routing workflow" section:

```
START → router ──route = "general"──→ general_chat ──→ END
               └─route = "study"────→ study_helper ──→ END
```

- **State fields:** the table from this story (`user_message`, `messages`, `route`, `final_answer`), noting it lives for one question and is never saved.
- **Node responsibilities:** router = ordinary Python `/study` rule (`choose_route()`), not an agent; general_chat = existing general-chat chain; study_helper = existing study-helper chain. Each answer node writes `final_answer`.
- **Edge rules:** `START → router`; router → `general_chat` or `study_helper` by `route`; each answer node → `END`. One pass, no loops.
- **Unchanged around the graph:** the chat endpoint, `chain_input()` history, Grok settings, normal JSON and streaming SSE replies, the development label, and Open WebUI.
- **Out of scope:** review or improve steps, loops, retries, more agents, tools, MCP, human approval, saved memory or databases, RAG, web search, observability platforms, deployment. Story 4.2 adds one bounded review step.

In the "Chain behaviours" table, note that both chains are now called from graph nodes.

### Commands to run

```bash
uv add langgraph
uv run ruff format src tests
uv run ruff check --fix src tests
uv run learning-companion     # starts on http://127.0.0.1:8000
```

Then send the two Open WebUI messages below. Record in the Handover the commands actually run and their results.

### Not in this story

Review or improver nodes, loops, retries, LLM-based routing, additional agents, tool execution, MCP, human approval, checkpointers or persistence, databases, RAG, web search, a new endpoint or second app, custom response fields, Open WebUI changes, a broad test suite, security programmes, observability platforms, deployment.

## Completion checks

1. `ruff format` and `ruff check` finish with no errors.
2. **General path:** in a new Open WebUI chat with the Learning Companion model selected, send *"Hi! Can you help me learn today?"*
   **Expected Open WebUI result:** the reply starts with `Route: general chat`, then a friendly Learning Companion answer that streams word by word and finishes cleanly, with no `Next step:` line.
   **Expected trace:** `route=general | graph: START → router → general_chat → END | …`
3. **Study path:** in the same chat, send *"/study Explain what an API is"*
   **Expected Open WebUI result:** the reply starts with `Route: study helper`, then a short, plain-language explanation of an API ending with exactly one `Next step:` line. It streams and finishes cleanly.
   **Expected trace:** `route=study | graph: START → router → study_helper → END | …`
4. Both trace lines show no key, instruction text, or message body, and both replies came through the same `POST /v1/chat/completions` endpoint with nothing changed in Open WebUI.

## Handover

- **Created:** `src/learning_companion/graph.py`.
- **Changed:** `src/learning_companion/main.py`, `pyproject.toml` and `uv.lock` (via `uv add langgraph` only), `docs/architecture.md`.
- **Unchanged:** `chain.py` (both chains, their instructions, `chain_input()`, `choose_route()`), `config.py`, `.env.example`, `try_study_helper.py`, tests, endpoints, request fields, response shapes, normal and streaming behaviour, Grok settings, history handling, and the Open WebUI connection.
- **Commands actually run:** _implementer fills in (expected: the four commands above, plus the two Open WebUI messages)._
- **Observed Open WebUI results and trace:** _implementer fills in (the labelled general reply and its `START → router → general_chat → END` line; the labelled study reply with its `Next step:` line and its `START → router → study_helper → END` line)._
- **Story 4.2 will extend:** this same graph with one bounded review path: a review step after an answer node that checks the `final_answer` and may ask for at most a fixed small number of improvements before going to `END`. The router, the two answer nodes, the endpoint, and the Open WebUI experience stay the same.
