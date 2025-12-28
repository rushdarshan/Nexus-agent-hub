#!/usr/bin/env python3
"""Connect to a running Edge (CDP) and run an Agent task:
Search the web for "10 Bible verses" and print results.

Usage:
  1) Start Edge with remote debugging (PowerShell):
     & "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\\Users\\rushd\\AppData\\Local\\Microsoft\\Edge\\User Data" --profile-directory="Default"

  2) Run this script:
     python examples/browser/connect_edge_agent.py
"""

import asyncio
from browser_use import Browser, Agent, ChatOpenAI


async def main():
    browser = Browser(cdp_url="http://localhost:9222", headless=False)

    # Uses OPENAI_API_KEY from environment
    llm = ChatOpenAI(model="gpt-4o-mini")

    agent = Agent(task="Search the web and list 10 Bible verses with short citations.", llm=llm, browser=browser)

    print("Running agent... (this will connect to Edge at http://localhost:9222)")
    try:
        result = await agent.run()
        print("Agent finished. Result:\n", result)
    except Exception as e:
        print("Agent run failed:", type(e).__name__, e)


def run():
    """Run the async main(), handling both fresh and nested event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        # No running loop — use asyncio.run()
        asyncio.run(main())
    else:
        # Already inside a running loop (e.g., Jupyter, VS Code execution)
        import nest_asyncio
        nest_asyncio.apply()
        loop.run_until_complete(main())


if __name__ == "__main__":
    run()
