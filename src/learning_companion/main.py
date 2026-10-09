import json
import time
import uuid
from typing import Literal

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from learning_companion.chain import build_chain
from learning_companion.config import settings

app = FastAPI(title="Learning Companion")


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    stream: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/models")
def list_models():
    data = []
    if settings.grok_model_name:
        data.append({"id": settings.grok_model_name, "object": "model", "created": 0, "owned_by": "xai"})
    return {"object": "list", "data": data}


def config_error() -> JSONResponse | None:
    for name, value in [
        ("GROK_API_KEY", settings.grok_api_key),
        ("GROK_MODEL_NAME", settings.grok_model_name),
    ]:
        if not value:
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "message": f"{name} is not set. Add it to your .env file and restart the app.",
                        "type": "configuration_error",
                    }
                },
            )
    return None


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    error = config_error()
    if error:
        return error

    question = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
    chain = build_chain()
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model = settings.grok_model_name

    if not request.stream:
        answer = await chain.ainvoke({"question": question})
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop",
                }
            ],
        }

    def chunk(delta: dict, finish_reason: str | None = None) -> str:
        payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        }
        return f"data: {json.dumps(payload)}\n\n"

    async def events():
        async for piece in chain.astream({"question": question}):
            if piece:
                yield chunk({"content": piece})
        yield chunk({}, "stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


def run():
    uvicorn.run("learning_companion.main:app", host=settings.host, port=settings.port)
