# Android-Use 📱🤖

**browser-use but for Android** - AI-powered Android device automation using vision and natural language.

Android-Use allows AI agents to see and interact with Android devices, similar to how browser-use automates web browsers. It uses computer vision and UI hierarchy understanding to accomplish tasks specified in natural language.

## ✨ Features

- 🎯 **AI-Powered Automation**: Natural language task execution using GPT-4o, Gemini, or other vision models
- 📸 **Vision + Hierarchy**: Combines screenshots with UI element analysis for accurate interaction
- 🛡️ **Safety Features**: Budget limits, loop detection, and error recovery
- 🔧 **Extensible Controller**: Register custom actions with decorators
- 🌐 **REST API**: FastAPI server for remote control and integration
- 📊 **Step Tracking**: Detailed history of all actions with screenshots
- 🔌 **Multiple LLM Providers**: OpenAI, OpenRouter, Google Gemini, Anthropic

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install uiautomator2 openai pillow python-dotenv fastapi uvicorn

# Connect your Android device via USB and enable USB debugging
adb devices
```

### Basic Usage

```python
import asyncio
from android_use import AndroidAgent, run_android_task

# Quick one-liner
async def main():
    result = await run_android_task("Open Settings and turn on WiFi")
    print(f"Success: {result.success}")
    print(f"Steps: {result.total_steps}")

asyncio.run(main())
```

### Full Control

```python
import asyncio
from android_use import Device, AndroidAgent, AgentConfig

async def main():
    # Connect to device
    device = Device()
    print(f"Connected to {device.info.model}")
    
    # Configure agent
    config = AgentConfig(
        max_steps=20,
        budget_limit=2.0,
        model="openai/gpt-4o-mini"
    )
    
    # Create and run agent
    agent = AndroidAgent(
        task="Open Chrome, search for 'Python tutorial', and click the first result",
        device=device,
        config=config
    )
    
    result = await agent.run()
    
    print(f"Task completed: {result.success}")
    print(f"Steps taken: {result.total_steps}")
    print(f"Time: {result.total_time:.1f}s")

asyncio.run(main())
```

### REST API

```python
from android_use import run_server

# Start the API server
run_server(host="0.0.0.0", port=8001)
```

Then use the API:

```bash
# Get device info
curl http://localhost:8001/api/device/info

# Take screenshot
curl http://localhost:8001/api/device/screenshot

# Tap at coordinates
curl -X POST http://localhost:8001/api/actions/tap \
  -H "Content-Type: application/json" \
  -d '{"x": 540, "y": 1200}'

# Run AI task
curl -X POST http://localhost:8001/api/agent/run_sync \
  -H "Content-Type: application/json" \
  -d '{"task": "Open Calculator and calculate 25 * 4"}'
```

## 📁 Project Structure

```
android_use/
├── __init__.py          # Main exports
├── config.py            # Global configuration
├── device/
│   └── device.py        # Device connection & actions
├── controller/
│   └── controller.py    # Action registry
├── hierarchy/
│   └── hierarchy.py     # UI element parsing
├── agent/
│   ├── agent.py         # AI agent logic
│   └── prompts.py       # System prompts
├── llm/
│   └── llm.py           # Multi-provider LLM client
├── server/
│   └── server.py        # FastAPI REST API
└── utils/
    └── logger.py        # Colored logging
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```env
# LLM Provider (choose one)
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Default device
ANDROID_SERIAL=your_device_serial
```

### Agent Configuration

```python
from android_use import AgentConfig

config = AgentConfig(
    max_steps=20,           # Maximum steps before stopping
    max_errors=3,           # Max consecutive errors
    step_delay=1.0,         # Delay between steps (seconds)
    budget_limit=2.0,       # Max cost in USD
    loop_detection_threshold=3,  # Stop after N identical actions
    save_screenshots=True,  # Save screenshots for debugging
    model="openai/gpt-4o-mini"  # LLM model
)
```

## 📱 Available Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `tap` | Tap at coordinates | `x`, `y` |
| `double_tap` | Double tap | `x`, `y` |
| `long_press` | Long press | `x`, `y`, `duration` |
| `swipe` | Swipe gesture | `x1`, `y1`, `x2`, `y2` |
| `swipe_up/down/left/right` | Directional swipe | - |
| `type_text` | Type text | `text`, `clear_first` |
| `press_key` | Press system key | `key` (home, back, enter, etc.) |
| `open_app` | Open app | `package` |
| `close_app` | Close app | `package` |
| `open_url` | Open URL | `url` |
| `wait` | Wait | `seconds` |
| `screenshot` | Save screenshot | `filename` |

## 🛡️ Safety Features

### Budget Protection
```python
config = AgentConfig(budget_limit=1.0)  # Stop if cost exceeds $1
```

### Loop Detection
```python
config = AgentConfig(loop_detection_threshold=3)  # Stop if same action repeated 3 times
```

### Manual Stop
```python
agent.stop()  # Gracefully stop the agent
```

## 🔌 Custom Actions

Register custom actions using decorators:

```python
from android_use import controller, ActionCategory

@controller.action(
    "take_photo",
    description="Take a photo using the camera",
    category=ActionCategory.APP
)
def take_photo(device):
    device.app_start("com.android.camera")
    device.wait(2)
    device.tap(540, 1900)  # Shutter button
```

## 📊 Callbacks

Track progress with callbacks:

```python
def on_step(step):
    print(f"Step {step.step_num}: {step.action} - {'✓' if step.success else '✗'}")
    print(f"  Reasoning: {step.reasoning}")

agent = AndroidAgent(
    task="...",
    on_step=on_step
)
```

## 🔗 Similar to browser-use

| browser-use | android-use |
|-------------|-------------|
| Browser | Device |
| BrowserSession | DeviceConfig |
| DOM | ViewHierarchy |
| Page | Screen |
| click() | tap() |
| type() | type_text() |
| scroll() | swipe_up/down() |

## 📄 License

MIT License - See LICENSE file for details.

## 🙏 Acknowledgments

Inspired by [browser-use](https://github.com/browser-use/browser-use) - the original AI browser automation framework.
