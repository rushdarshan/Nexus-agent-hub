#!/usr/bin/env python3
"""
CLI Agent Runner - Runs a single agent task from command line argument.
Used by the dashboard to spawn agents in separate processes.
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Setup
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

# Force UTF-8 output for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

from browser_use import Agent, BrowserProfile, BrowserSession
from browser_use.llm import ChatGoogle


async def run_task(task: str):
    """Run a single browser agent task via Intelligent Router."""
    print(f"\n🚀 Starting Nexus Router with task: {task}\n")
    
    llm = ChatGoogle(model="gemini-2.0-flash", temperature=0.3)
    
    from intelligent_router import NexusRouter
    router = NexusRouter(llm=llm)
    
    try:
        # The router handles the execution and printing
        await router.execute(task)
        print(f"\n✅ Task completed via Nexus Router!")
        return "Success"
        
    except Exception as e:
        print(f"\n❌ Nexus Router failed: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cli_agent.py <task>")
        print("Example: python cli_agent.py \"Go to google.com and search for weather\"")
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    
    try:
        asyncio.run(run_task(task))
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
