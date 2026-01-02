"""
Android Device - Full session management for Android automation
Mirrors browser-use's Browser/BrowserSession architecture
"""

import uiautomator2 as u2
from pathlib import Path
from PIL import Image
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import io
import base64

logger = logging.getLogger('android_use.device')


@dataclass
class DeviceConfig:
    """Configuration for Android device connection"""
    serial: Optional[str] = None
    timeout: float = 30.0
    screenshot_quality: int = 90
    output_dir: Path = field(default_factory=lambda: Path("android_output"))
    auto_init: bool = True  # Auto-initialize uiautomator service
    record_video: bool = False
    demo_mode: bool = False
    demo_delay: float = 0.5


@dataclass  
class DeviceInfo:
    """Device information container"""
    serial: str
    product_name: str
    brand: str
    model: str
    sdk_version: int
    screen_width: int
    screen_height: int
    android_version: str
    
    @classmethod
    def from_device(cls, device: u2.Device) -> 'DeviceInfo':
        info = device.info
        window_size = device.window_size()
        return cls(
            serial=device.serial or "unknown",
            product_name=info.get('productName', 'Unknown'),
            brand=info.get('brand', 'Unknown'),
            model=info.get('model', 'Unknown'),
            sdk_version=info.get('sdkInt', 0),
            screen_width=window_size[0],
            screen_height=window_size[1],
            android_version=info.get('androidVersion', 'Unknown')
        )


class Device:
    """
    Wrapper for Android device interaction using uiautomator2.
    Provides full session management mirroring browser-use's BrowserSession.
    """
    
    def __init__(self, config: Optional[DeviceConfig] = None, serial: str = None):
        """
        Initialize device connection.
        
        Args:
            config: DeviceConfig instance with all settings
            serial: Quick shorthand for config.serial
        """
        self.config = config or DeviceConfig(serial=serial)
        self._device: Optional[u2.Device] = None
        self._info: Optional[DeviceInfo] = None
        self._connected = False
        self._screenshot_count = 0
        self._action_history: List[Dict[str, Any]] = []
        
        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-connect
        self.connect()
    
    @property
    def device(self) -> u2.Device:
        """Get the underlying uiautomator2 device"""
        if not self._device:
            raise RuntimeError("Device not connected. Call connect() first.")
        return self._device
    
    @property
    def info(self) -> DeviceInfo:
        """Get device information"""
        if not self._info:
            self._info = DeviceInfo.from_device(self.device)
        return self._info
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def connect(self) -> 'Device':
        """Establish connection to Android device"""
        try:
            logger.info(f"Connecting to device: {self.config.serial or 'auto-detect'}")
            self._device = u2.connect(self.config.serial)
            
            if self.config.auto_init:
                # Initialize uiautomator service on device (API varies by version)
                try:
                    if hasattr(self._device, 'uiautomator'):
                        self._device.uiautomator.start()
                    elif hasattr(self._device, 'start_uiautomator'):
                        self._device.start_uiautomator()
                except Exception:
                    pass  # Service may already be running
            
            self._info = DeviceInfo.from_device(self._device)
            self._connected = True
            
            logger.info(f"✓ Connected to {self.info.brand} {self.info.model}")
            logger.info(f"  Screen: {self.info.screen_width}x{self.info.screen_height}")
            logger.info(f"  Android {self.info.android_version} (API {self.info.sdk_version})")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to connect to device: {e}")
            raise ConnectionError(f"Could not connect to Android device: {e}")
    
    def disconnect(self):
        """Disconnect from device"""
        if self._device:
            try:
                self._device.uiautomator.stop()
            except:
                pass
            self._device = None
            self._connected = False
            logger.info("Disconnected from device")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    # ========== Screenshot Methods ==========
    
    def get_screenshot(self, save: bool = False) -> Image.Image:
        """
        Capture and return screenshot as PIL Image.
        
        Args:
            save: If True, also save to output directory
        """
        img = self.device.screenshot()
        self._screenshot_count += 1
        
        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.config.output_dir / f"screenshot_{self._screenshot_count}_{timestamp}.png"
            img.save(path, quality=self.config.screenshot_quality)
            logger.debug(f"Screenshot saved: {path}")
        
        return img
    
    def get_screenshot_base64(self) -> str:
        """Get screenshot as base64 encoded string"""
        img = self.get_screenshot()
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def save_screenshot(self, filename: str = None) -> Path:
        """Save screenshot and return path"""
        img = self.get_screenshot()
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        path = self.config.output_dir / filename
        img.save(path)
        return path
    
    # ========== Hierarchy Methods ==========
    
    def get_hierarchy(self, compressed: bool = True) -> str:
        """Dump device hierarchy as XML string"""
        return self.device.dump_hierarchy(compressed=compressed)
    
    def get_current_app(self) -> Dict[str, str]:
        """Get current foreground app info"""
        info = self.device.app_current()
        return {
            'package': info.get('package', ''),
            'activity': info.get('activity', '')
        }
    
    # ========== Action Methods ==========
    
    def _record_action(self, action: str, params: Dict[str, Any]):
        """Record action for history"""
        self._action_history.append({
            'action': action,
            'params': params,
            'timestamp': datetime.now().isoformat()
        })
        
        if self.config.demo_mode:
            time.sleep(self.config.demo_delay)
    
    def click(self, x: int, y: int):
        """Click at coordinates (x, y)"""
        self._record_action('click', {'x': x, 'y': y})
        self.device.click(x, y)
        logger.debug(f"Click: ({x}, {y})")
    
    def tap(self, x: int, y: int):
        """Alias for click"""
        self.click(x, y)
    
    def double_click(self, x: int, y: int):
        """Double click at coordinates"""
        self._record_action('double_click', {'x': x, 'y': y})
        self.device.double_click(x, y)
    
    def long_click(self, x: int, y: int, duration: float = 1.0):
        """Long press at coordinates"""
        self._record_action('long_click', {'x': x, 'y': y, 'duration': duration})
        self.device.long_click(x, y, duration=duration)
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        """Swipe from (x1, y1) to (x2, y2)"""
        self._record_action('swipe', {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
        self.device.swipe(x1, y1, x2, y2, duration=duration)
    
    def swipe_up(self, scale: float = 0.5):
        """Swipe up on screen"""
        h = self.info.screen_height
        w = self.info.screen_width
        center_x = w // 2
        start_y = int(h * 0.7)
        end_y = int(h * 0.3)
        self.swipe(center_x, start_y, center_x, end_y)
    
    def swipe_down(self, scale: float = 0.5):
        """Swipe down on screen"""
        h = self.info.screen_height
        w = self.info.screen_width
        center_x = w // 2
        start_y = int(h * 0.3)
        end_y = int(h * 0.7)
        self.swipe(center_x, start_y, center_x, end_y)
    
    def swipe_left(self):
        """Swipe left on screen"""
        h = self.info.screen_height
        w = self.info.screen_width
        center_y = h // 2
        self.swipe(int(w * 0.8), center_y, int(w * 0.2), center_y)
    
    def swipe_right(self):
        """Swipe right on screen"""
        h = self.info.screen_height
        w = self.info.screen_width
        center_y = h // 2
        self.swipe(int(w * 0.2), center_y, int(w * 0.8), center_y)
    
    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        """Drag from one point to another"""
        self._record_action('drag', {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
        self.device.drag(x1, y1, x2, y2, duration=duration)
    
    def pinch_in(self, percent: int = 50, steps: int = 50):
        """Pinch in gesture (zoom out)"""
        self._record_action('pinch_in', {'percent': percent})
        self.device.pinch_in(percent=percent, steps=steps)
    
    def pinch_out(self, percent: int = 50, steps: int = 50):
        """Pinch out gesture (zoom in)"""
        self._record_action('pinch_out', {'percent': percent})
        self.device.pinch_out(percent=percent, steps=steps)
    
    # ========== Input Methods ==========
    
    def keyevent(self, key: str):
        """Press a device key (e.g., 'home', 'back', 'enter')"""
        self._record_action('keyevent', {'key': key})
        self.device.press(key)
    
    def press(self, key: str):
        """Alias for keyevent"""
        self.keyevent(key)
    
    def press_back(self):
        """Press back button"""
        self.keyevent('back')
    
    def press_home(self):
        """Press home button"""
        self.keyevent('home')
    
    def press_recent(self):
        """Press recent apps button"""
        self.keyevent('recent')
    
    def press_enter(self):
        """Press enter key"""
        self.keyevent('enter')
    
    def type_text(self, text: str, clear_first: bool = False):
        """Type text into focused element"""
        self._record_action('type_text', {'text': text})
        if clear_first:
            self.device.clear_text()
        self.device.send_keys(text)
    
    def clear_text(self):
        """Clear text in focused field"""
        self._record_action('clear_text', {})
        self.device.clear_text()
    
    # ========== App Management ==========
    
    def app_start(self, package_name: str, activity: str = None, wait: bool = True):
        """Start an application"""
        self._record_action('app_start', {'package': package_name})
        self.device.app_start(package_name, activity=activity, wait=wait)
        logger.info(f"Started app: {package_name}")
    
    def app_stop(self, package_name: str):
        """Stop an application"""
        self._record_action('app_stop', {'package': package_name})
        self.device.app_stop(package_name)
    
    def app_stop_all(self):
        """Stop all running apps"""
        self.device.app_stop_all()
    
    def app_install(self, apk_path: str):
        """Install an APK"""
        self.device.app_install(apk_path)
    
    def app_uninstall(self, package_name: str):
        """Uninstall an app"""
        self.device.app_uninstall(package_name)
    
    def app_list(self, filter: str = None) -> List[str]:
        """List installed apps"""
        return self.device.app_list(filter=filter)
    
    def open_url(self, url: str):
        """Open URL in default browser"""
        self._record_action('open_url', {'url': url})
        self.device.open_url(url)
    
    # ========== Element Finding ==========
    
    def find_element(self, **kwargs) -> Optional[u2.UiObject]:
        """
        Find element by attributes.
        Examples:
            device.find_element(text="Login")
            device.find_element(resourceId="com.app:id/button")
            device.find_element(className="android.widget.Button")
        """
        try:
            return self.device(**kwargs)
        except Exception:
            return None
    
    def find_and_click(self, **kwargs) -> bool:
        """Find element and click it"""
        elem = self.find_element(**kwargs)
        if elem and elem.exists:
            elem.click()
            return True
        return False
    
    def wait_for_element(self, timeout: float = 10.0, **kwargs) -> bool:
        """Wait for element to appear"""
        elem = self.find_element(**kwargs)
        if elem:
            return elem.wait(timeout=timeout)
        return False
    
    # ========== Utility Methods ==========
    
    def wait(self, seconds: float):
        """Wait for specified seconds"""
        time.sleep(seconds)
    
    def wake_up(self):
        """Wake up device screen"""
        self.device.screen_on()
    
    def sleep(self):
        """Put device screen to sleep"""
        self.device.screen_off()
    
    def unlock(self):
        """Unlock device (simple swipe unlock)"""
        self.device.unlock()
    
    def get_action_history(self) -> List[Dict[str, Any]]:
        """Get history of all actions performed"""
        return self._action_history.copy()
    
    def clear_action_history(self):
        """Clear action history"""
        self._action_history.clear()
    
    @staticmethod
    def list_devices() -> List[str]:
        """List all connected Android devices via ADB"""
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True
            )
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = []
            for line in lines:
                if '\tdevice' in line:
                    devices.append(line.split('\t')[0])
            return devices
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []
