"""
FastAPI Server for Android-Use
REST API for Android device automation
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import asyncio
import uvicorn
import logging
from pathlib import Path
from datetime import datetime
import base64
import io

from ..device.device import Device, DeviceConfig, DeviceInfo
from ..hierarchy.hierarchy import ViewHierarchy
from ..agent.agent import AndroidAgent, AgentConfig, AgentResult, AgentStatus
from ..controller.controller import controller

logger = logging.getLogger('android_use.server')

# ========== Pydantic Models ==========

class TaskRequest(BaseModel):
    task: str = Field(..., description="The task to accomplish")
    max_steps: int = Field(20, description="Maximum steps to take")
    model: str = Field("openai/gpt-4o-mini", description="LLM model to use")


class TapRequest(BaseModel):
    x: int
    y: int


class SwipeRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    duration: float = 0.5


class TypeRequest(BaseModel):
    text: str
    clear_first: bool = False


class AppRequest(BaseModel):
    package: str


class UrlRequest(BaseModel):
    url: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    steps_completed: int
    current_action: Optional[str] = None


# ========== FastAPI App ==========

def create_app(device: Device = None) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="Android-Use API",
        description="REST API for AI-powered Android automation (browser-use for Android)",
        version="1.0.0"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # State
    _device: Optional[Device] = device
    _running_tasks: Dict[str, Dict] = {}
    _task_counter = 0
    
    # ========== Device Endpoints ==========
    
    @app.get("/")
    async def root():
        return {
            "name": "android-use",
            "version": "1.0.0",
            "description": "browser-use but for Android",
            "docs": "/docs"
        }
    
    @app.get("/api/device/connect")
    async def connect_device(serial: str = None):
        """Connect to Android device"""
        nonlocal _device
        try:
            _device = Device(serial=serial)
            return {
                "success": True,
                "device": {
                    "serial": _device.info.serial,
                    "model": _device.info.model,
                    "brand": _device.info.brand,
                    "screen": f"{_device.info.screen_width}x{_device.info.screen_height}",
                    "android": _device.info.android_version
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/device/info")
    async def get_device_info():
        """Get device information"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        return {
            "serial": _device.info.serial,
            "model": _device.info.model,
            "brand": _device.info.brand,
            "screen_width": _device.info.screen_width,
            "screen_height": _device.info.screen_height,
            "android_version": _device.info.android_version,
            "sdk_version": _device.info.sdk_version
        }
    
    @app.get("/api/device/screenshot")
    async def get_screenshot(format: str = "base64"):
        """Get device screenshot"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        
        try:
            img = _device.get_screenshot()
            
            if format == "file":
                path = _device.save_screenshot()
                return FileResponse(path)
            else:
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                b64 = base64.b64encode(buffer.getvalue()).decode()
                return {"screenshot": b64}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/device/hierarchy")
    async def get_hierarchy(format: str = "summary"):
        """Get UI hierarchy"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        
        try:
            xml = _device.get_hierarchy()
            hierarchy = ViewHierarchy(xml)
            
            if format == "xml":
                return {"hierarchy": xml}
            elif format == "json":
                return {"elements": hierarchy.to_dict_list()}
            else:
                return {"summary": hierarchy.to_indexed_prompt()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/device/current_app")
    async def get_current_app():
        """Get current foreground app"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        return _device.get_current_app()
    
    # ========== Action Endpoints ==========
    
    @app.post("/api/actions/tap")
    async def action_tap(req: TapRequest):
        """Tap at coordinates"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.tap(req.x, req.y)
        return {"success": True, "action": "tap", "params": {"x": req.x, "y": req.y}}
    
    @app.post("/api/actions/swipe")
    async def action_swipe(req: SwipeRequest):
        """Swipe gesture"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.swipe(req.x1, req.y1, req.x2, req.y2, req.duration)
        return {"success": True, "action": "swipe"}
    
    @app.post("/api/actions/swipe_up")
    async def action_swipe_up():
        """Swipe up (scroll down)"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.swipe_up()
        return {"success": True, "action": "swipe_up"}
    
    @app.post("/api/actions/swipe_down")
    async def action_swipe_down():
        """Swipe down (scroll up)"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.swipe_down()
        return {"success": True, "action": "swipe_down"}
    
    @app.post("/api/actions/type")
    async def action_type(req: TypeRequest):
        """Type text"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.type_text(req.text, req.clear_first)
        return {"success": True, "action": "type", "text": req.text}
    
    @app.post("/api/actions/press/{key}")
    async def action_press(key: str):
        """Press system key (back, home, recent, enter)"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.keyevent(key)
        return {"success": True, "action": "press", "key": key}
    
    @app.post("/api/actions/open_app")
    async def action_open_app(req: AppRequest):
        """Open an application"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.app_start(req.package)
        return {"success": True, "action": "open_app", "package": req.package}
    
    @app.post("/api/actions/close_app")
    async def action_close_app(req: AppRequest):
        """Close an application"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.app_stop(req.package)
        return {"success": True, "action": "close_app", "package": req.package}
    
    @app.post("/api/actions/open_url")
    async def action_open_url(req: UrlRequest):
        """Open URL in browser"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        _device.open_url(req.url)
        return {"success": True, "action": "open_url", "url": req.url}
    
    # ========== Agent Endpoints ==========
    
    @app.post("/api/agent/run")
    async def run_agent_task(req: TaskRequest, background_tasks: BackgroundTasks):
        """Run an AI agent task"""
        nonlocal _task_counter
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        
        _task_counter += 1
        task_id = f"task_{_task_counter}_{datetime.now().strftime('%H%M%S')}"
        
        _running_tasks[task_id] = {
            "task": req.task,
            "status": "starting",
            "steps": [],
            "result": None
        }
        
        async def run_task():
            try:
                config = AgentConfig(
                    max_steps=req.max_steps,
                    model=req.model
                )
                
                def on_step(step):
                    _running_tasks[task_id]["steps"].append({
                        "num": step.step_num,
                        "action": step.action,
                        "success": step.success
                    })
                    _running_tasks[task_id]["status"] = "running"
                
                agent = AndroidAgent(
                    task=req.task,
                    device=_device,
                    config=config,
                    on_step=on_step
                )
                
                result = await agent.run()
                
                _running_tasks[task_id]["status"] = result.status.value
                _running_tasks[task_id]["result"] = {
                    "success": result.success,
                    "message": result.final_message,
                    "total_steps": result.total_steps,
                    "time": result.total_time
                }
            except Exception as e:
                _running_tasks[task_id]["status"] = "failed"
                _running_tasks[task_id]["result"] = {"error": str(e)}
        
        background_tasks.add_task(run_task)
        
        return {
            "task_id": task_id,
            "status": "started",
            "task": req.task
        }
    
    @app.get("/api/agent/status/{task_id}")
    async def get_task_status(task_id: str):
        """Get status of a running task"""
        if task_id not in _running_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        return _running_tasks[task_id]
    
    @app.post("/api/agent/run_sync")
    async def run_agent_task_sync(req: TaskRequest):
        """Run an AI agent task synchronously (blocks until complete)"""
        if not _device:
            raise HTTPException(status_code=400, detail="No device connected")
        
        try:
            config = AgentConfig(
                max_steps=req.max_steps,
                model=req.model
            )
            
            agent = AndroidAgent(
                task=req.task,
                device=_device,
                config=config
            )
            
            result = await agent.run()
            
            return {
                "success": result.success,
                "status": result.status.value,
                "message": result.final_message,
                "total_steps": result.total_steps,
                "time": result.total_time,
                "steps": [
                    {
                        "num": s.step_num,
                        "action": s.action,
                        "params": s.params,
                        "reasoning": s.reasoning,
                        "success": s.success
                    }
                    for s in result.steps
                ]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/actions/available")
    async def get_available_actions():
        """Get list of available actions"""
        return {"actions": controller.get_action_schema()}
    
    return app


def run_server(host: str = "0.0.0.0", port: int = 8001, device_serial: str = None):
    """Run the API server"""
    device = Device(serial=device_serial) if device_serial else None
    app = create_app(device)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
