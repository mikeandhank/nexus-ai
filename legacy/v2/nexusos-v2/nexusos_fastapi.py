"""
FastAPI Migration Module
=========================
Migrate from Flask to FastAPI for native async support
"""
from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
import asyncio
from typing import AsyncGenerator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print("Starting NexusOS FastAPI...")
    yield
    print("Shutting down NexusOS...")


app = FastAPI(
    title="NexusOS API",
    description="Enterprise AI Agent Operating System",
    version="6.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
async def status():
    return {
        "running": True,
        "version": "6.0.0",
        "framework": "FastAPI",
        "components": {"postgresql": True, "redis": True, "ollama": True, "celery": True}
    }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    
    async def generate():
        response = f"Echo: {message}"
        for word in response.split():
            yield f"data: {word}\n\n"
            await asyncio.sleep(0.05)
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/agents")
async def list_agents():
    return {"agents": []}


@app.post("/api/agents")
async def create_agent(request: Request):
    body = await request.json()
    return {"agent_id": "new-agent", "name": body.get("name")}


@app.get("/api/metrics")
async def metrics():
    return {"total_requests": 0, "total_tokens": 0, "total_cost_usd": 0.0}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception:
        pass