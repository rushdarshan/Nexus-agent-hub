"""
Android Automation Agent with AI Vision
High-performance agent refactored for production use
"""

import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import os

import uiautomator2 as u2
from dotenv import load_dotenv
import openai

# Import agent-fuse for budget limits and loop detection
try:
    from agent_fuse import init as agent_fuse_init, check_loop, SentinelLoopError, SentinelBudgetExceeded
    HAS_AGENT_FUSE = True
except ImportError:
    HAS_AGENT_FUSE = False

load_dotenv()

class AndroidAgent:
    """Production-ready AI-powered Android automation agent"""
    
    def __init__(self, workspace: str = "./android_output", budget: float = 2.0):
        """Initialize Android agent with budget protection"""
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        if HAS_AGENT_FUSE:
            # Initialize agent-fuse with budget limit
            agent_fuse_init(
                budget=budget,
                fail_safe=True,
                loop_threshold=3,
                loop_detection_enabled=True
            )
            print(f"💰 Budget protection enabled: ${budget:.2f}")
        
        # Connect to Android device
        print("📱 Connecting to Android device...")
        try:
            self.device = u2.connect()
            info = self.device.info
            self.device_info = {
                'model': info.get('productName', 'Unknown'),
                'width': info.get('displayWidth', 1080),
                'height': info.get('displayHeight', 2400),
                'android_version': info.get('sdkInt', 0)
            }
            print(f"✅ Connected to {self.device_info['model']} ({self.device_info['width']}x{self.device_info['height']})")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            raise

        # Initialize OpenRouter/Gemini client
        api_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ No API key found in .env (OPENROUTER_API_KEY or GEMINI_API_KEY)")
            
        base_url = os.getenv('BASE_URL', 'https://openrouter.ai/api/v1')
        model = os.getenv('MODEL_NAME', 'openai/gpt-4o-mini')

        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        
        self.action_history = []

    def capture_screenshot(self) -> str:
        """Capture screenshot and save to workspace"""
        screenshot = self.device.screenshot()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.workspace / f"screenshot_{timestamp}.png"
        screenshot.save(screenshot_path)
        return str(screenshot_path)
    
    def screenshot_to_base64(self, screenshot_path: str) -> str:
        """Convert screenshot to base64 for API"""
        with open(screenshot_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def get_view_hierarchy_summary(self) -> str:
        """Get simplified view hierarchy with clickable elements"""
        try:
            xml = self.device.dump_hierarchy(compressed=True)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            
            elements = []
            for node in root.iter():
                clickable = node.get('clickable') == 'true'
                text = node.get('text', '')
                desc = node.get('content-desc', '')
                if clickable or text or desc:
                    elements.append({
                        'text': text or desc,
                        'bounds': node.get('bounds', ''),
                        'clickable': clickable
                    })
            
            return str(elements[:30]) # Limit to 30 elements for context window
        except:
            return "View hierarchy unavailable"

    async def analyze_screen_and_decide(self, task: str, step: int, screenshot_path: str) -> Optional[Dict[str, Any]]:
        """Use AI Vision to decide next action"""
        screenshot_b64 = self.screenshot_to_base64(screenshot_path)
        view_summary = self.get_view_hierarchy_summary()

        prompt = f"""You are an Android automation agent.
TASK: {task}
STEP: {step}/20
SCREEN: {self.device_info['width']}x{self.device_info['height']}

CLICKABLE ELEMENTS:
{view_summary}

PREVIOUS ACTIONS:
{json.dumps(self.action_history[-3:], indent=2) if self.action_history else 'None'}

INSTRUCTIONS:
1. Analyze the screenshot and clickable elements.
2. If the task is completed, set "task_complete" to true.
3. Otherwise, provide the next action.

RESPONSE FORMAT (JSON):
{{
    "task_complete": bool,
    "reasoning": "string",
    "next_action": {{
        "type": "tap|swipe|type_text|press_back|press_home|wait",
        "x": int,
        "y": int,
        "text": "optional",
        "end_x": int, (for swipe)
        "end_y": int, (for swipe)
        "description": "string"
    }}
}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{screenshot_b64}'}}
                        ]
                    }
                ],
                max_tokens=500,
                response_format={ "type": "json_object" }
            )
            
            data = json.loads(response.choices[0].message.content)
            if data.get('task_complete'):
                print(f"🏁 Task complete: {data.get('reasoning')}")
                return None
            return data.get('next_action')
        except Exception as e:
            print(f"❌ AI error: {e}")
            return None

    def execute_action(self, action: Dict[str, Any]) -> bool:
        """Execute the chosen action on the device"""
        action_type = action.get('type')
        
        if HAS_AGENT_FUSE:
            try:
                check_loop(action_type, action)
            except SentinelLoopError:
                print("🚨 Loop detected! Executing failsafe back button.")
                self.device.press('back')
                return False

        try:
            if action_type == 'tap':
                self.device.click(action['x'], action['y'])
                print(f"👆 Tap: ({action['x']}, {action['y']}) - {action.get('description')}")
            elif action_type == 'swipe':
                self.device.swipe(action['x'], action['y'], action['end_x'], action['end_y'])
                print(f"🔄 Swipe: ({action['x']}, {action['y']}) to ({action['end_x']}, {action['end_y']})")
            elif action_type == 'type_text':
                self.device.send_keys(action['text'])
                print(f"✏️ Type: {action['text']}")
            elif action_type == 'press_back':
                self.device.press('back')
                print("◀️ Press Back")
            elif action_type == 'press_home':
                self.device.press('home')
                print("🏠 Press Home")
            elif action_type == 'wait':
                time.sleep(action.get('duration', 2))
                print(f"⏳ Wait: {action.get('duration', 2)}s")
            return True
        except Exception as e:
            print(f"❌ Action failed: {e}")
            return False

    async def run(self, task: str, max_steps: int = 20):
        """Run the automation loop"""
        print(f"🚀 Starting task: {task}")
        for step in range(1, max_steps + 1):
            print(f"\n📍 Step {step}/{max_steps}")
            screenshot = self.capture_screenshot()
            
            try:
                action = await self.analyze_screen_and_decide(task, step, screenshot)
            except Exception as e:
                if "SentinelBudgetExceeded" in str(e):
                    print("💰 Budget exceeded! Stopping.")
                    break
                raise

            if not action:
                break

            success = self.execute_action(action)
            self.action_history.append({'step': step, 'action': action, 'success': success})
            await asyncio.sleep(1)
        
        print("\n✨ Automation session finished")

if __name__ == "__main__":
    async def main():
        agent = AndroidAgent()
        await agent.run("Open settings and check about phone")
    
    asyncio.run(main())
