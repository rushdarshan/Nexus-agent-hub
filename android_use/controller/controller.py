"""
Android Controller - Registry for agent actions
Mirrors browser-use's Controller architecture with decorators
"""

import asyncio
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import functools

logger = logging.getLogger('android_use.controller')


class ActionCategory(Enum):
    """Categories for organizing actions"""
    NAVIGATION = "navigation"
    INPUT = "input"
    GESTURE = "gesture"
    APP = "app"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass
class ActionInfo:
    """Metadata about a registered action"""
    name: str
    description: str
    category: ActionCategory
    params: Dict[str, str]  # param_name -> description
    func: Callable
    requires_element: bool = False
    is_async: bool = False


class AndroidController:
    """
    Registry for actions that the Agent can perform on the Device.
    Uses decorators to register actions, similar to browser-use's controller.
    """
    
    def __init__(self):
        self.actions: Dict[str, ActionInfo] = {}
        self._setup_default_actions()
    
    def action(
        self, 
        name: str, 
        description: str = "",
        category: ActionCategory = ActionCategory.CUSTOM,
        params: Dict[str, str] = None,
        requires_element: bool = False
    ):
        """
        Decorator to register a new action.
        
        Example:
            @controller.action("custom_scroll", description="Scroll to element")
            def custom_scroll(device, direction: str):
                ...
        """
        def decorator(func: Callable):
            is_async = asyncio.iscoroutinefunction(func)
            
            self.actions[name] = ActionInfo(
                name=name,
                description=description or func.__doc__ or f"Execute {name}",
                category=category,
                params=params or {},
                func=func,
                requires_element=requires_element,
                is_async=is_async
            )
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    async def execute_action(
        self, 
        device, 
        name: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a registered action on the device.
        
        Returns:
            Dict with 'success' bool and optional 'result' or 'error'
        """
        if name not in self.actions:
            available = list(self.actions.keys())
            logger.error(f"Action '{name}' not registered. Available: {available}")
            return {
                'success': False,
                'error': f"Action '{name}' is not registered. Available actions: {available}"
            }
        
        action_info = self.actions[name]
        
        try:
            logger.info(f"⚡ Executing: {name} with {params}")
            
            if action_info.is_async:
                result = await action_info.func(device, **params)
            else:
                result = action_info.func(device, **params)
            
            return {'success': True, 'result': result}
            
        except Exception as e:
            logger.error(f"Action '{name}' failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_action_schema(self) -> List[Dict[str, Any]]:
        """
        Get schema of all available actions for LLM consumption.
        Returns list of action definitions.
        """
        schema = []
        for name, info in self.actions.items():
            schema.append({
                'name': name,
                'description': info.description,
                'category': info.category.value,
                'parameters': info.params,
                'requires_element': info.requires_element
            })
        return schema
    
    def get_actions_prompt(self) -> str:
        """Get formatted string of actions for LLM prompt"""
        lines = ["Available Actions:"]
        
        by_category: Dict[str, List[ActionInfo]] = {}
        for info in self.actions.values():
            cat = info.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(info)
        
        for category, actions in by_category.items():
            lines.append(f"\n[{category.upper()}]")
            for action in actions:
                param_str = ", ".join(f"{k}: {v}" for k, v in action.params.items()) if action.params else "none"
                lines.append(f"  • {action.name}: {action.description}")
                lines.append(f"    params: {{{param_str}}}")
        
        return "\n".join(lines)
    
    def _setup_default_actions(self):
        """Register all default actions"""
        
        # ========== Navigation Actions ==========
        
        @self.action(
            "tap",
            description="Tap at screen coordinates",
            category=ActionCategory.NAVIGATION,
            params={"x": "X coordinate (int)", "y": "Y coordinate (int)"}
        )
        def tap(device, x: int, y: int):
            device.click(int(x), int(y))
        
        @self.action(
            "double_tap",
            description="Double tap at coordinates",
            category=ActionCategory.NAVIGATION,
            params={"x": "X coordinate", "y": "Y coordinate"}
        )
        def double_tap(device, x: int, y: int):
            device.double_click(int(x), int(y))
        
        @self.action(
            "long_press",
            description="Long press at coordinates",
            category=ActionCategory.NAVIGATION,
            params={"x": "X coordinate", "y": "Y coordinate", "duration": "Hold time in seconds (default 1.0)"}
        )
        def long_press(device, x: int, y: int, duration: float = 1.0):
            device.long_click(int(x), int(y), duration=duration)
        
        # ========== Gesture Actions ==========
        
        @self.action(
            "swipe",
            description="Swipe from one point to another",
            category=ActionCategory.GESTURE,
            params={"x1": "Start X", "y1": "Start Y", "x2": "End X", "y2": "End Y", "duration": "Duration (default 0.5)"}
        )
        def swipe(device, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
            device.swipe(int(x1), int(y1), int(x2), int(y2), duration=duration)
        
        @self.action(
            "swipe_up",
            description="Swipe up on screen to scroll down",
            category=ActionCategory.GESTURE,
            params={}
        )
        def swipe_up(device):
            device.swipe_up()
        
        @self.action(
            "swipe_down",
            description="Swipe down on screen to scroll up",
            category=ActionCategory.GESTURE,
            params={}
        )
        def swipe_down(device):
            device.swipe_down()
        
        @self.action(
            "swipe_left",
            description="Swipe left on screen",
            category=ActionCategory.GESTURE,
            params={}
        )
        def swipe_left(device):
            device.swipe_left()
        
        @self.action(
            "swipe_right",
            description="Swipe right on screen",
            category=ActionCategory.GESTURE,
            params={}
        )
        def swipe_right(device):
            device.swipe_right()
        
        @self.action(
            "pinch_in",
            description="Pinch in gesture (zoom out)",
            category=ActionCategory.GESTURE,
            params={"percent": "Pinch percent (default 50)"}
        )
        def pinch_in(device, percent: int = 50):
            device.pinch_in(percent=percent)
        
        @self.action(
            "pinch_out",
            description="Pinch out gesture (zoom in)",
            category=ActionCategory.GESTURE,
            params={"percent": "Pinch percent (default 50)"}
        )
        def pinch_out(device, percent: int = 50):
            device.pinch_out(percent=percent)
        
        @self.action(
            "drag",
            description="Drag from one point to another",
            category=ActionCategory.GESTURE,
            params={"x1": "Start X", "y1": "Start Y", "x2": "End X", "y2": "End Y"}
        )
        def drag(device, x1: int, y1: int, x2: int, y2: int):
            device.drag(int(x1), int(y1), int(x2), int(y2))
        
        # ========== Input Actions ==========
        
        @self.action(
            "type_text",
            description="Type text into the currently focused input field",
            category=ActionCategory.INPUT,
            params={"text": "Text to type", "clear_first": "Clear field first (default False)"}
        )
        def type_text(device, text: str, clear_first: bool = False):
            device.type_text(text, clear_first=clear_first)
        
        @self.action(
            "clear_text",
            description="Clear text in the currently focused field",
            category=ActionCategory.INPUT,
            params={}
        )
        def clear_text(device):
            device.clear_text()
        
        @self.action(
            "press_key",
            description="Press a system key (home, back, recent, enter, etc.)",
            category=ActionCategory.INPUT,
            params={"key": "Key name (home|back|recent|enter|delete|search|volume_up|volume_down)"}
        )
        def press_key(device, key: str):
            device.keyevent(key)
        
        @self.action(
            "press_back",
            description="Press the back button",
            category=ActionCategory.INPUT,
            params={}
        )
        def press_back(device):
            device.press_back()
        
        @self.action(
            "press_home",
            description="Press the home button",
            category=ActionCategory.INPUT,
            params={}
        )
        def press_home(device):
            device.press_home()
        
        @self.action(
            "press_enter",
            description="Press enter/submit",
            category=ActionCategory.INPUT,
            params={}
        )
        def press_enter(device):
            device.press_enter()
        
        # ========== App Actions ==========
        
        @self.action(
            "open_app",
            description="Open an application by package name",
            category=ActionCategory.APP,
            params={"package": "App package name (e.g., com.android.chrome)"}
        )
        def open_app(device, package: str):
            device.app_start(package)
        
        @self.action(
            "close_app",
            description="Close an application",
            category=ActionCategory.APP,
            params={"package": "App package name to close"}
        )
        def close_app(device, package: str):
            device.app_stop(package)
        
        @self.action(
            "open_url",
            description="Open a URL in the default browser",
            category=ActionCategory.APP,
            params={"url": "URL to open"}
        )
        def open_url(device, url: str):
            device.open_url(url)
        
        # ========== System Actions ==========
        
        @self.action(
            "wait",
            description="Wait for specified seconds",
            category=ActionCategory.SYSTEM,
            params={"seconds": "Number of seconds to wait"}
        )
        async def wait(device, seconds: float):
            await asyncio.sleep(float(seconds))
        
        @self.action(
            "screenshot",
            description="Take and save a screenshot",
            category=ActionCategory.SYSTEM,
            params={"filename": "Optional filename for the screenshot"}
        )
        def screenshot(device, filename: str = None):
            return device.save_screenshot(filename)
        
        @self.action(
            "wake",
            description="Wake up the device screen",
            category=ActionCategory.SYSTEM,
            params={}
        )
        def wake(device):
            device.wake_up()
        
        @self.action(
            "sleep",
            description="Put device screen to sleep",
            category=ActionCategory.SYSTEM,
            params={}
        )
        def sleep_device(device):
            device.sleep()
        
        @self.action(
            "done",
            description="Signal that the task is complete",
            category=ActionCategory.SYSTEM,
            params={"message": "Completion message"}
        )
        def done(device, message: str = "Task completed"):
            logger.info(f"✓ Task completed: {message}")
            return {"done": True, "message": message}


# Default Controller Instance
controller = AndroidController()
