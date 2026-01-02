"""
Test Android agent with simple task
"""

import asyncio
from android_agent_simple import AndroidAgent


async def test_simple_task():
    agent = AndroidAgent()
    
    # Very simple task
    task = "Press the home button"
    
    result = await agent.run(task, max_steps=3)
    
    print("\n✅ Task completed!")
    print(f"Steps taken: {result['steps']}")


if __name__ == "__main__":
    asyncio.run(test_simple_task())
