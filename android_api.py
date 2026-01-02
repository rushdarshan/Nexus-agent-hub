"""
Android Automation API
FastAPI endpoints for Android device control
Integrates with existing browser-use setup
"""

import asyncio
import base64
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uiautomator2 as u2

from android_agent import AndroidAgent

app = FastAPI(title="Android + Browser Automation API")

# Add CORS for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
android_agent: Optional[AndroidAgent] = None
device: Optional[u2.Device] = None


@app.on_event("startup")
async def startup():
    """Initialize Android agent on startup"""
    global android_agent, device
    try:
        android_agent = AndroidAgent()
        device = android_agent.device
        print("✅ Android agent initialized")
    except Exception as e:
        print(f"⚠️ Android agent not initialized: {e}")
        print("   Server will start but Android endpoints will fail")


class TaskRequest(BaseModel):
    task: str
    max_steps: int = 10


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


# ============= Android Device Info =============

@app.get("/api/android/info")
async def get_device_info():
    """Get connected Android device information"""
    if not device:
        raise HTTPException(status_code=503, detail="No Android device connected")
    
    info = device.info
    return {
        "model": info.get('productName', 'Unknown'),
        "screen_width": info.get('displayWidth', 0),
        "screen_height": info.get('displayHeight', 0),
        "android_version": info.get('sdkInt', 0),
        "battery": info.get('battery', {}),
    }


@app.get("/api/android/devices")
async def list_devices():
    """List all connected Android devices"""
    import subprocess
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')[1:]
    
    devices = []
    for line in lines:
        if line.strip() and 'device' in line:
            device_id = line.split()[0]
            devices.append({'id': device_id, 'status': 'device'})
    
    return {"devices": devices}


# ============= Screenshot & Screen Streaming =============

@app.get("/api/android/screenshot")
async def get_screenshot():
    """Get current Android screen as base64"""
    if not device:
        raise HTTPException(status_code=503, detail="No device connected")
    
    try:
        screenshot = device.screenshot()
        
        # Convert to base64
        from io import BytesIO
        buffer = BytesIO()
        screenshot.save(buffer, format='PNG')
        screenshot_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            "screenshot": screenshot_b64,
            "width": screenshot.size[0],
            "height": screenshot.size[1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/android/current_app")
async def get_current_app():
    """Get currently active app"""
    if not device:
        raise HTTPException(status_code=503, detail="No device connected")
    
    try:
        app_info = device.app_current()
        return {
            "package": app_info.get('package'),
            "activity": app_info.get('activity')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= AI Automation =============

@app.post("/api/android/execute_task")
async def execute_android_task(request: TaskRequest):
    """Execute AI-powered automation task on Android"""
    if not android_agent:
        raise HTTPException(status_code=503, detail="Android agent not initialized")
    
    try:
        result = await android_agent.run(request.task, request.max_steps)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= Manual Control =============

@app.post("/api/android/tap")
async def tap(request: TapRequest):
    """Tap at specific coordinates"""
    if not device:
        raise HTTPException(status_code=503, detail="No device connected")
    
    try:
        device.click(request.x, request.y)
        return {"status": "success", "x": request.x, "y": request.y}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/android/swipe")
async def swipe(request: SwipeRequest):
    """Swipe from one point to another"""
    if not device:
        raise HTTPException(status_code=503, detail="No device connected")
    
    try:
        device.swipe(request.x1, request.y1, request.x2, request.y2, duration=request.duration)
        return {
            "status": "success",
            "from": {"x": request.x1, "y": request.y1},
            "to": {"x": request.x2, "y": request.y2}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/android/type")
async def type_text(request: TypeRequest):
    """Type text on Android"""
    if not device:
        raise HTTPException(status_code=503, detail="No device connected")
    
    try:
        device.send_keys(request.text)
        return {"status": "success", "text": request.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/android/press/{button}")
async def press_button(button: str):
    """Press Android button (back, home, recent, etc.)"""
    if not device:
        raise HTTPException(status_code=503, detail="No device connected")
    
    valid_buttons = ['back', 'home', 'recent', 'menu', 'power', 'volume_up', 'volume_down']
    if button not in valid_buttons:
        raise HTTPException(status_code=400, detail=f"Invalid button. Use: {valid_buttons}")
    
    try:
        device.press(button)
        return {"status": "success", "button": button}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= App Management =============

@app.post("/api/android/launch_app")
async def launch_app(package: str):
    """Launch Android app by package name"""
    if not device:
        raise HTTPException(status_code=503, detail="No device connected")
    
    try:
        device.app_start(package)
        return {"status": "success", "package": package}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/android/stop_app")
async def stop_app(package: str):
    """Stop Android app"""
    if not device:
        raise HTTPException(status_code=503, detail="No device connected")
    
    try:
        device.app_stop(package)
        return {"status": "success", "package": package}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= Health Check =============

@app.get("/api/android/health")
async def health_check():
    """Check if Android automation is available"""
    return {
        "status": "healthy" if device else "no_device",
        "agent_initialized": android_agent is not None,
        "device_connected": device is not None
    }


# Run with: uvicorn android_api:app --reload --port 8001
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
