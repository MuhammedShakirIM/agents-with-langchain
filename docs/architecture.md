# Architecture — Learning Companion Chatbot

## The one classroom flow

```
Open WebUI  →  our local app (OpenAI-compatible chat endpoint)  →  LangChain prompt + Grok model  →  answer back in Open WebUI
```

A participant types a question in Open WebUI. Open WebUI sends it to our small app running on their laptop. Our app wraps the question in a fixed Learning Companion prompt, sends it to Grok through LangChain, and returns the answer to Open WebUI.

## Open WebUI's role

Open WebUI is already installed and working for every participant. It is the supplied chat window and nothing more. Participants do not reinstall, reconfigure, modify, or build Open WebUI. They only add our app as a connection in its settings.

## What we are building

A small Learning Companion Chatbot: one local Python app that Open WebUI talks to. It is not a custom frontend and not a second demonstration app.

## The three endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Confirms the app is running. |
| `GET /v1/models` | Tells Open WebUI which model it can pick (the configured Grok model). |
| `POST /v1/chat/completions` | Takes the chat and returns the answer. The same route handles both normal (all at once) and streaming (word by word) answers. |

## Light boundaries

- API keys live only in an untracked `.env` file. It is never committed.
- The application's instructions (the system prompt) are kept separate from the user's messages.

## Out of scope for this course

Authentication, authorization, security hardening, databases, persistent memory, RAG, production deployment, and extensive tests.

## Tech choices

Python 3.12, `uv`, FastAPI, Pydantic settings, LangChain, `langchain-xai` (the Grok integration, class `ChatXAI`), Uvicorn, Ruff, pytest.
