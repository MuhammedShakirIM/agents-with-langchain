# Manual tests

## Story 1.1 — Architecture and Project Seed

**What it adds:** a local Learning Companion app with health, model-list, and OpenAI-compatible chat endpoints that answer through LangChain and Grok.

Prerequisite: copy `.env.example` to `.env`, set `GROK_API_KEY` and `GROK_MODEL_NAME`, then start the app with `uv run learning-companion`. The `model` field in chat requests is ignored; the app always uses `GROK_MODEL_NAME`.

```bash
curl http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}`.

```bash
curl http://127.0.0.1:8000/v1/models
```

Expected: `"object":"list"` with one entry whose `id` is your `GROK_MODEL_NAME` and `owned_by` is `xai`.

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "learning-companion", "messages": [{"role": "user", "content": "What is a variable in Python?"}], "stream": false}'
```

Expected: HTTP 200, `"object":"chat.completion"`, one choice with `message.role` `assistant`, a friendly Learning Companion explanation in `message.content`, and `finish_reason` `stop`.

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "learning-companion", "messages": [{"role": "user", "content": "Explain a for loop in one paragraph."}], "stream": true}'
```

Expected: a stream of `chat.completion.chunk` events with `delta.content` pieces, then a chunk with an empty `delta` and `finish_reason` `stop`, and the response ends with `data: [DONE]`.

```bash
# Blank GROK_API_KEY in .env, restart the app, then:
curl -i http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "learning-companion", "messages": [{"role": "user", "content": "Hello"}]}'
```

Expected: HTTP 503 with `{"error":{"message":"GROK_API_KEY is not set. Add it to your .env file and restart the app.","type":"configuration_error"}}`, and the app keeps running.
