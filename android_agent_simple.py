"""
Simple Android Automation Agent with AI Vision
Uses OpenRouter (GPT-4o-mini) to analyze screenshots and control Android device
"""

import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import os

import uiautomator2 as u2
from dotenv import load_dotenv
import openai

# Import agent-fuse for budget limits and loop detection
from agent_fuse import init as agent_fuse_init, check_loop, SentinelLoopError, SentinelBudgetExceeded

load_dotenv()


class AndroidAgent:
    """AI-powered Android automation agent"""
    
    def __init__(self, workspace: str = "./android_output", budget: float = 2.0):
        """Initialize Android agent with budget protection"""
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Initialize agent-fuse with budget limit
        agent_fuse_init(
            budget=budget,  # Max spend in USD
            fail_safe=True,  # Stop if budget exceeded
            loop_threshold=3,  # Error after 3 identical actions
            loop_detection_enabled=True
        )
        print(f"💰 Budget protection: Max ${budget:.2f} per session")
        print(f"🔄 Loop detection: Max 3 identical actions")
        
        # Connect to Android device
        print("📱 Connecting to Android device...")
        self.device = u2.connect()
        
        # Get device info
        info = self.device.info
        self.device_info = {
            'model': info.get('productName', 'Unknown'),
            'width': info.get('displayWidth', 1080),
            'height': info.get('displayHeight', 2400),
            'android_version': info.get('sdkInt', 0)
        }
        print(f"✅ Connected to {self.device_info['model']}")
        print(f"   Screen: {self.device_info['width']}x{self.device_info['height']}")
        
        # Initialize OpenRouter client
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv('OPENROUTER_API_KEY'),
            base_url='https://openrouter.ai/api/v1'
        )
        
        self.action_history = []
        
    def capture_screenshot(self) -> str:
        """Capture screenshot and save to workspace"""
        screenshot = self.device.screenshot()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.workspace / f"screenshot_{timestamp}.png"
        screenshot.save(screenshot_path)
        print(f"📸 Screenshot: {screenshot_path}")
        return str(screenshot_path)
    
    def screenshot_to_base64(self, screenshot_path: str) -> str:
        """Convert screenshot to base64 for API"""
        with open(screenshot_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def get_view_hierarchy_summary(self) -> str:
        """Get simplified view hierarchy with clickable elements"""
        try:
            xml = self.device.dump_hierarchy(compressed=True)
            # Parse XML and extract clickable elements
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            
            clickable_elements = []
            for node in root.iter():
                if node.get('clickable') == 'true' or node.get('text'):
                    text = node.get('text', '')
                    content_desc = node.get('content-desc', '')
                    bounds = node.get('bounds', '')
                    
                    if text or content_desc:
                        clickable_elements.append({
                            'text': text or content_desc,
                            'bounds': bounds
                        })
            
            # Return summary
            if len(clickable_elements) > 20:
                return f"Found {len(clickable_elements)} elements. Key elements: " + str(clickable_elements[:15])
            return str(clickable_elements)
        except:
            return "Could not parse view hierarchy"
    
    def is_stuck_in_loop(self) -> bool:
        """Detect if agent is repeating the same action"""
        if len(self.action_history) < 3:
            return False
        
        last_3_actions = self.action_history[-3:]
        # Check if all 3 have same coordinates
        coords = [(a['action'].get('x'), a['action'].get('y')) for a in last_3_actions]
        return len(set(coords)) == 1
    
    async def analyze_screen_and_decide(
        self,
        task: str,
        step: int,
        screenshot_path: str
    ) -> Optional[Dict[str, Any]]:
        """Use AI to analyze screen and decide next action"""
        
        # Check if stuck in loop
        if self.is_stuck_in_loop():
            print("⚠️ STUCK IN LOOP - Trying press_back")
            return {
                'type': 'press_back',
                'description': 'Unstuck by going back',
                'confidence': 0.9
            }
        
        screenshot_b64 = self.screenshot_to_base64(screenshot_path)
        view_summary = self.get_view_hierarchy_summary()
        
        # Build prompt
        prompt = f"""You are an Android automation agent. Analyze the screenshot and decide the next action.

TASK: {task}
STEP: {step}/10

DEVICE INFO:
- Screen: {self.device_info['width']}x{self.device_info['height']}
- Model: {self.device_info['model']}

CLICKABLE ELEMENTS ON SCREEN:
{view_summary}

PREVIOUS ACTIONS (last 3):
{json.dumps(self.action_history[-3:], indent=2) if self.action_history else 'None'}

⚠️ IMPORTANT: DO NOT repeat the same action if it didn't work last time!

INSTRUCTIONS:
1. Look at the screenshot AND the list of clickable elements
2. Match text/descriptions to what you see in the image
3. Determine if the task is COMPLETE (if you see "About Phone" or similar, task is done!)
4. OR decide a DIFFERENT action if previous didn't work

RESPONSE FORMAT (JSON only):
{{
    "task_complete": false,
    "reasoning": "Detailed explanation of what you see and why this action",
    "next_action": {{
        "type": "tap",
        "x": 540,
        "y": 1200,
        "description": "Tapping on [specific element name from list]",
        "confidence": 0.95
    }}
}}

ACTION TYPES:
- tap: Single touch at (x, y)
- swipe: Drag down/up for scrolling - add "end_x", "end_y"
- type_text: Type text - add "text" field
- press_back: Press back button (USE THIS if you're lost or stuck!)
- press_home: Press home button
- wait: Pause - add "duration" in seconds

COORDINATE TIPS:
- Top of screen (status bar): y = 100
- Bottom of screen (nav bar): y = 2300
- Center: x = 540, y = 1200
- Use element bounds if available!

If task is COMPLETE or you see target screen, return: {{"task_complete": true, "reasoning": "I can see About Phone / target screen"}}
"""
        
        try:
            # Call OpenRouter with vision
            response = await self.client.chat.completions.create(
                model='openai/gpt-4o-mini',
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/png;base64,{screenshot_b64}'
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            print(f"\n🧠 AI Response:\n{response_text}\n")
            
            # Extract JSON
            response_json = self._parse_json(response_text)
            
            if response_json.get('task_complete'):
                print("✅ AI determined task is complete")
                return None
            
            return response_json.get('next_action')
            
        except Exception as e:
            print(f"❌ AI analysis error: {e}")
            return None
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from response"""
        # Remove markdown code blocks
        text = text.replace('```json\n', '').replace('\n```', '')
        text = text.replace('```\n', '').replace('\n```', '')
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in text
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {'task_complete': True}
    
    def execute_action(self, action: Dict[str, Any]) -> bool:
        """Execute action on Android device with loop protection"""
        action_type = action.get('type')
        
        # Check for loops using agent-fuse
        try:
            action_signature = f"{action_type}_{action.get('x', 0)}_{action.get('y', 0)}"
            check_loop(action_type, action)
        except SentinelLoopError as e:
            print(f"🚨 LOOP DETECTED! {e}")
            print(f"   Action repeated {e.call_count} times")
            print(f"   Trying press_back instead...")
            self.device.press('back')
            time.sleep(2)
            return False
        
        try:
            if action_type == 'tap':
                x, y = action['x'], action['y']
                desc = action.get('description', '')
                print(f"👆 Tapping at ({x}, {y}) - {desc}")
                self.device.click(x, y)
                return True
            
            elif action_type == 'swipe':
                x1, y1 = action['x'], action['y']
                x2, y2 = action['end_x'], action['end_y']
                print(f"🔄 Swiping ({x1},{y1}) → ({x2},{y2})")
                self.device.swipe(x1, y1, x2, y2)
                return True
            
            elif action_type == 'type_text':
                text = action['text']
                print(f"✏️ Typing: {text}")
                self.device.send_keys(text)
                return True
            
            elif action_type == 'press_back':
                print("◀️ Pressing back")
                self.device.press('back')
                return True
            
            elif action_type == 'press_home':
                print("🏠 Pressing home")
                self.device.press('home')
                return True
            
            elif action_type == 'wait':
                duration = action.get('duration', 2)
                print(f"⏳ Waiting {duration}s")
                time.sleep(duration)
                return True
            
            else:
                print(f"⚠️ Unknown action: {action_type}")
                return False
                
        except Exception as e:
            print(f"❌ Action failed: {e}")
            return False
    
    async def run(self, task: str, max_steps: int = 10) -> Dict[str, Any]:
        """Execute automation task with budget protection"""
        print("=" * 60)
        print(f"🎯 TASK: {task}")
        print("=" * 60)
        
        step = 0
        try:
            while step < max_steps:
                step += 1
                print(f"\n📍 Step {step}/{max_steps}")
                
                # Capture screen
                screenshot_path = self.capture_screenshot()
                
                # Get AI decision (protected by agent-fuse budget)
                try:
                    action = await self.analyze_screen_and_decide(task, step, screenshot_path)
                except SentinelBudgetExceeded as e:
                    print(f"\n💰 BUDGET EXCEEDED: {e}")
                    print("   Stopping to protect your wallet!")
                    break
                
                if action is None:
                    print("\n✅ Task completed!")
                    break
                
                # Execute action (with loop detection)
                success = self.execute_action(action)
                
                # Record history
                self.action_history.append({
                    'step': step,
                    'action': action,
                    'success': success,
                    'screenshot': screenshot_path
                })
                
                # Brief pause for UI updates
                await asyncio.sleep(1.5)
        
        except SentinelBudgetExceeded as e:
            print(f"\n💰 BUDGET EXCEEDED: {e}")
        except KeyboardInterrupt:
            print("\n⏹️  Stopped by user")
        
        print("\n" + "=" * 60)
        print(f"✅ Finished in {step} steps")
        
        # Show spend summary
        from agent_fuse import monitor
        stats = monitor()
        print(f"💰 Total spend: ${stats.total_spend_usd:.4f}")
        print(f"💰 Budget remaining: ${stats.budget_remaining_usd:.2f}")
        print("=" * 60)
        
        return {
            'status': 'success',
            'task': task,
            'steps': step,
            'history': self.action_history
        }


async def main():
    """Example usage"""
    agent = AndroidAgent(budget=1.0)  # Only spend max $1
    
    # Simpler task that's easier to complete
    task = "Press the home button"
    
    result = await agent.run(task, max_steps=3)
    
    print("\n📊 RESULTS:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
