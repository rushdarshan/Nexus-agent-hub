
import sys
from pathlib import Path

# Add current dir to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from manager import manager
from memory import memory

app = FastAPI()

# Enable CORS for development (allowing frontend to connect from localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


class TaskRequest(BaseModel):
    task: str
    mode: str | None = None
    openrouter_key: str | None = None


@app.post("/agent/start")
async def start_agent(request: TaskRequest):
    try:
        await manager.start_task(request.task)
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/swarm/start")
async def start_swarm(request: TaskRequest):
    try:
        mode = request.mode or "simulate"
        await manager.start_swarm(request.task, mode=mode, openrouter_key=request.openrouter_key)
        return {"status": "swarm_started", "mode": mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/stop")
async def stop_agent():
    await manager.stop()
    return {"status": "stopped"}


@app.post("/agent/pause")
async def pause_agent():
    await manager.pause()
    return {"status": "paused"}


@app.post("/agent/resume")
async def resume_agent():
    await manager.resume()
    return {"status": "resumed"}


@app.get("/memory/stats")
async def get_memory_stats():
    return memory.get_stats()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def send_update(data: dict):
        try:
            await websocket.send_json(data)
        except Exception:
            pass  # Handle disconnects gracefully in the manager logic if needed

    manager.add_listener(send_update)

    try:
        while True:
            # Keep connection open; optionally listen for client commands
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.remove_listener(send_update)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.remove_listener(send_update)
