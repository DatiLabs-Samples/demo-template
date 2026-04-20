# Backend Guidelines — Python FastAPI

Stack: Python 3.12+ | FastAPI | uvicorn | boto3 | python-dotenv

## App Setup

```python
# app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Demo", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Run: `uvicorn app.main:app --reload --port 8000` (use `--workers 1` for WebSocket demos).

## Configuration

```python
# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "default")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
```

Rules:
- Every env var has a sensible default
- Static config (prompts, constants) lives in `config.py`, not `.env`
- Never put secrets in `config.py`

## REST Endpoints

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    session_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = await invoke_model(req.message)
    return ChatResponse(reply=result["reply"], session_id=result["session_id"])
```

Register with `app.include_router(router)`.

## WebSocket Pattern

```python
@app.websocket("/ws/voice")
async def voice_ws(ws: WebSocket):
    await ws.accept()
    session = None
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            if msg["type"] == "start":
                if session: await session.stop()
                session = create_session(ws, msg)
                await session.start()
                await safe_send(ws, {"type": "started"})
            elif msg["type"] == "audio":
                if session: await session.send_audio(msg["data"])
            elif msg["type"] == "stop":
                if session: await session.stop(); session = None
                await safe_send(ws, {"type": "stopped"})
    except WebSocketDisconnect:
        pass
    finally:
        if session: await session.stop()
```

Safe send helper:
```python
async def safe_send(ws: WebSocket, message: dict):
    try: await ws.send_text(json.dumps(message))
    except Exception: pass
```

Callback pattern for streaming services:
```python
async def on_audio(b64): await safe_send(ws, {"type": "audio", "data": b64})
async def on_text(text, role): await safe_send(ws, {"type": "text", "data": text, "role": role})
async def on_error(err): await safe_send(ws, {"type": "error", "data": err})
session = StreamingService(on_audio, on_text, on_error)
```

## AWS Service Integration

```python
import boto3
from app.config import AWS_REGION, AWS_PROFILE

def get_boto3_session():
    return boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)

def get_client(service_name):
    return get_boto3_session().client(service_name)
```

For Smithy-based SDKs (Nova Sonic, etc.) that don't read boto3 profiles:
```python
def resolve_credentials_for_smithy(profile_name, region):
    import os
    session = boto3.Session(profile_name=profile_name)
    creds = session.get_credentials().get_frozen_credentials()
    os.environ["AWS_ACCESS_KEY_ID"] = creds.access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = creds.secret_key
    if creds.token: os.environ["AWS_SESSION_TOKEN"] = creds.token
    return session.region_name or region
```

Async with boto3 (synchronous SDK):
```python
import asyncio

async def invoke_model(prompt, model_id):
    client = get_client("bedrock-runtime")
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: client.invoke_model(...))
    return json.loads(response["body"].read())
```

## Streaming Patterns

| Pattern   | Use case                    | Direction       |
|-----------|-----------------------------|-----------------|
| REST      | CRUD, one-shot queries      | Request/Response|
| SSE       | Text generation, progress   | Server → Client |
| WebSocket | Voice chat, real-time audio | Bidirectional   |

SSE example:
```python
from fastapi.responses import StreamingResponse

@router.post("/api/generate")
async def generate(req: ChatRequest):
    async def stream():
        for chunk in bedrock_stream(req.message):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")
```

## Error Handling

```python
class AppException(Exception):
    def __init__(self, message, status_code=500, detail=None):
        self.message, self.status_code, self.detail = message, status_code, detail

@app.exception_handler(AppException)
async def handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message, "detail": exc.detail})
```

All errors return: `{"error": "message", "detail": "optional"}`

## Logging

```python
logger = logging.getLogger(__name__)

logger.info("WebSocket client connected")     # Connection lifecycle
logger.exception("WebSocket error")           # Errors with traceback
logger.debug(f"Message type: {msg_type}")     # Debug details
```

Rules: one logger per module, never log secrets, use `.exception()` inside except blocks.

## Dependencies

Pin exact versions in `requirements.txt`:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
websockets==14.1
boto3==1.35.86
python-dotenv==1.0.1
```

Setup: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
