"""
Setup:
1. Get your API key from https://cloud.browser-use.com/new-api-key
2. Set environment variable: export BROWSER_USE_API_KEY="your-key"
"""

from dotenv import load_dotenv
import asyncio
import sys
import os

# Fix Windows asyncio subprocess issue
if sys.platform == 'win32':
	asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from browser_use import Agent, Browser
from browser_use.llm.openrouter.chat import ChatOpenRouter

load_dotenv()

async def main():
	# Set workspace to your actual directory
	workspace_dir = r'c:\Users\rushd\Downloads\Onboarding Screen Design\browser-use'
	os.chdir(workspace_dir)
	
	# Use your existing Chrome profile (Darshan)
	chrome_user_data_dir = r'C:\Users\rushd\AppData\Local\Google\Chrome\User Data'
	
	browser = Browser(
		headless=False,
		use_cloud=False,
		user_data_dir=chrome_user_data_dir,  # Use your existing Chrome profile
	)
	
	# Use OpenRouter LLM with your API key
	llm = ChatOpenRouter(
		model='openai/gpt-4o-mini',
		api_key=os.getenv('OPENROUTER_API_KEY'),
		base_url='https://openrouter.ai/api/v1'
	)
	
	agent = Agent(
		task='Find the number of stars of the following repos: browser-use, playwright, stagehand, react, nextjs',
		llm=llm,
		browser=browser,
	)
	
	history = await agent.run()
	return history

if __name__ == '__main__':
	asyncio.run(main())
