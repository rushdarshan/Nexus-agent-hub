"""
Unified Browser + Android Agent
Control both web browsers AND Android devices from one agent
"""

import asyncio
import sys
import os
from pathlib import Path

# Fix Windows asyncio subprocess issue
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv
from browser_use import Agent, Browser
from browser_use.llm.openrouter.chat import ChatOpenRouter

# Import Android agent
from android_agent_simple import AndroidAgent

load_dotenv()


class UnifiedAgent:
    """Control both browser and Android device"""
    
    def __init__(self, workspace: str = "./unified_output"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Initialize LLM
        self.llm = ChatOpenRouter(
            model='openai/gpt-4o-mini',
            api_key=os.getenv('OPENROUTER_API_KEY'),
            base_url='https://openrouter.ai/api/v1'
        )
        
        # Initialize browser agent (local Chrome)
        print("🌐 Initializing browser agent...")
        self.browser = Browser(
            headless=False,
            use_cloud=False,
            user_data_dir=r'C:\Users\rushd\AppData\Local\Google\Chrome\User Data'
        )
        
        # Initialize Android agent
        print("📱 Initializing Android agent...")
        self.android_agent = AndroidAgent(workspace=str(self.workspace / "android"))
    
    async def run_browser_task(self, task: str):
        """Execute task in web browser"""
        print("\n" + "="*60)
        print(f"🌐 BROWSER TASK: {task}")
        print("="*60)
        
        agent = Agent(
            task=task,
            llm=self.llm,
            browser=self.browser,
        )
        
        result = await agent.run()
        return result
    
    async def run_android_task(self, task: str, max_steps: int = 10):
        """Execute task on Android device"""
        print("\n" + "="*60)
        print(f"📱 ANDROID TASK: {task}")
        print("="*60)
        
        result = await self.android_agent.run(task, max_steps)
        return result
    
    async def run_cross_platform_workflow(self):
        """Example: Coordinate tasks across browser AND Android"""
        print("\n" + "="*60)
        print("🔄 CROSS-PLATFORM WORKFLOW")
        print("="*60)
        
        # Step 1: Get information from web
        browser_result = await self.run_browser_task(
            "Go to GitHub and find the browser-use repository star count"
        )
        
        # Step 2: Do something on Android with that info
        android_result = await self.run_android_task(
            "Open Notes app and create a new note",
            max_steps=5
        )
        
        print("\n✅ Cross-platform workflow complete!")
        return {
            'browser': browser_result,
            'android': android_result
        }


async def demo_browser_only():
    """Demo: Browser automation only"""
    agent = UnifiedAgent()
    await agent.run_browser_task(
        "Search Google for 'Python automation' and click the first result"
    )


async def demo_android_only():
    """Demo: Android automation only"""
    agent = UnifiedAgent()
    await agent.run_android_task(
        "Open Calculator app and add 5 + 3",
        max_steps=5
    )


async def demo_both():
    """Demo: Both platforms"""
    agent = UnifiedAgent()
    
    # Option 1: Sequential tasks
    print("\n📋 Running tasks sequentially...")
    
    # Browser first
    await agent.run_browser_task("Open GitHub trending page")
    
    # Then Android
    await agent.run_android_task("Open Settings", max_steps=3)
    
    print("\n✅ Both platforms tested!")


async def demo_cross_platform():
    """Demo: Cross-platform workflow"""
    agent = UnifiedAgent()
    await agent.run_cross_platform_workflow()


def main():
    """Choose your demo"""
    print("="*60)
    print("🤖 UNIFIED BROWSER + ANDROID AGENT")
    print("="*60)
    print("\nAvailable demos:")
    print("1. Browser only")
    print("2. Android only")
    print("3. Both (sequential)")
    print("4. Cross-platform workflow")
    print("\n0. Custom tasks")
    
    choice = input("\nChoose demo (1-4, or 0): ").strip()
    
    if choice == '1':
        asyncio.run(demo_browser_only())
    elif choice == '2':
        asyncio.run(demo_android_only())
    elif choice == '3':
        asyncio.run(demo_both())
    elif choice == '4':
        asyncio.run(demo_cross_platform())
    elif choice == '0':
        # Custom
        browser_task = input("Browser task (or skip): ").strip()
        android_task = input("Android task (or skip): ").strip()
        
        async def custom():
            agent = UnifiedAgent()
            if browser_task:
                await agent.run_browser_task(browser_task)
            if android_task:
                await agent.run_android_task(android_task)
        
        asyncio.run(custom())
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()
