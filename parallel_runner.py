#!/usr/bin/env python3
"""
PARALLEL AGENT RUNNER - Run 4 Agents Simultaneously
====================================================
Spawns 4 browser agents, each with their own task, running in parallel.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from browser_use import Agent, BrowserProfile, BrowserSession
from browser_use.llm import ChatGoogle

# Check API Key
if "GOOGLE_API_KEY" not in os.environ:
    print("❌ GOOGLE_API_KEY not set. Please create a .env file or export the variable.")
    sys.exit(1)

# Define 4 different tasks for the agents
AGENT_TASKS = [
    {
        "name": "Agent 1 - News",
        "task": "Go to Google News and find the top 3 headlines today. Return them as a numbered list."
    },
    {
        "name": "Agent 2 - Weather",
        "task": "Search Google for 'weather in New York' and tell me the current temperature and conditions."
    },
    {
        "name": "Agent 3 - Stock",
        "task": "Search Google for 'AAPL stock price' and tell me the current price of Apple stock."
    },
    {
        "name": "Agent 4 - Wikipedia",
        "task": "Go to Wikipedia and search for 'Artificial Intelligence'. Return the first paragraph of the article."
    }
]

async def run_single_agent(task_info: dict, agent_id: int):
    """Run a single agent with its assigned task."""
    print(f"\n🚀 [{task_info['name']}] Starting...")
    
    llm = ChatGoogle(model="gemini-2.0-flash", temperature=0.3)
    
    # Each agent gets its own browser session
    browser_session = BrowserSession(
        browser_profile=BrowserProfile(
            headless=False,  # Set to True for background execution
            disable_security=True
        )
    )
    
    try:
        agent = Agent(
            task=task_info['task'],
            llm=llm,
            browser_session=browser_session
        )
        
        result = await agent.run(max_steps=15)
        
        print(f"\n✅ [{task_info['name']}] COMPLETED")
        print(f"   Result: {result.final_result() if hasattr(result, 'final_result') else 'Task completed'}")
        
        return {
            "agent": task_info['name'],
            "success": True,
            "result": str(result.final_result()) if hasattr(result, 'final_result') else "Completed"
        }
        
    except Exception as e:
        print(f"\n❌ [{task_info['name']}] FAILED: {e}")
        return {
            "agent": task_info['name'],
            "success": False,
            "error": str(e)
        }
    finally:
        try:
            await browser_session.close()
        except:
            pass


async def run_parallel_agents():
    """Run all 4 agents in parallel."""
    print("=" * 60)
    print("🔥 PARALLEL AGENT RUNNER - 4 Agents Starting")
    print("=" * 60)
    
    # Create tasks for all agents
    tasks = [
        run_single_agent(task_info, idx)
        for idx, task_info in enumerate(AGENT_TASKS)
    ]
    
    # Run all agents concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  Agent {i+1}: ❌ Exception - {result}")
        elif result.get('success'):
            print(f"  {result['agent']}: ✅ Success")
        else:
            print(f"  {result['agent']}: ❌ Failed - {result.get('error', 'Unknown')}")
    
    print("=" * 60)
    print("🏁 All agents finished!")
    

if __name__ == "__main__":
    try:
        asyncio.run(run_parallel_agents())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
