import asyncio
from android_use import AndroidAgent
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Example: Check About Phone
    task = "Find the 'About Phone' section in Settings"
    agent = AndroidAgent(task=task, max_steps=10)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
